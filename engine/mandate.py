"""Het Levensmandaat: de klant schrijft de regels, de agent handelt erbinnen.

beslis() is puur: dezelfde actie en hetzelfde mandaat geven altijd dezelfde
beslissing. Het vastleggen (tijd, hashketen) gebeurt in engine.audit.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

UITGEVOERD = "Executed"
VRAAG = "Asks first"
GEBLOKKEERD = "Blocked"
SOORTEN = ("energie", "betaling", "overschrijving_spaargeld")


@dataclass(frozen=True)
class Mandaat:
    buffer_maanden_min: int = 3
    vraag_boven: int = 500
    energie_auto_besparing: int = 100
    blokkeer_nieuwe_begunstigde_nacht: bool = True

    def __post_init__(self) -> None:
        if not 1 <= self.buffer_maanden_min <= 24:
            raise ValueError("buffer_maanden_min moet tussen 1 en 24 liggen")
        if self.vraag_boven < 0:
            raise ValueError("vraag_boven mag niet negatief zijn")
        if self.energie_auto_besparing < 0:
            raise ValueError("energie_auto_besparing mag niet negatief zijn")

    def regels(self) -> list[str]:
        r = [
            f"My emergency buffer never drops below {self.buffer_maanden_min} months of expenses.",
            f"Anything above €{self.vraag_boven}: ask me first.",
            f"Switch to cheaper energy if I save more than €{self.energie_auto_besparing} a year.",
        ]
        if self.blokkeer_nieuwe_begunstigde_nacht:
            r.append("A large amount at night to a new payee: always block it and call me.")
        return r


@dataclass(frozen=True)
class Actie:
    id: str
    omschrijving: str
    soort: str            # energie | betaling | overschrijving_spaargeld
    bedrag: float
    besparing_per_jaar: float = 0
    nieuwe_begunstigde: bool = False
    uur: int = 14
    context: str = ""

    def __post_init__(self) -> None:
        if self.soort not in SOORTEN:
            raise ValueError(f"onbekende soort {self.soort!r}")
        if not 0 <= self.uur <= 23:
            raise ValueError("uur moet tussen 0 en 23 liggen")
        if self.bedrag < 0 or self.besparing_per_jaar < 0:
            raise ValueError("bedrag en besparing mogen niet negatief zijn")


DEMO_ACTIES: tuple[Actie, ...] = (
    Actie("A1", "Energy agent: a contract that is €140 a year cheaper", "energie", 0, besparing_per_jaar=140, uur=10,
          context="Negotiated by your agent with the supplier's agent."),
    Actie("A2", "Payment of €600 to Garage Janssens", "betaling", 600, uur=11, context="Known payee."),
    Actie("A4", "€35,000 from savings to an investment account", "overschrijving_spaargeld", 35_000, uur=14,
          context="Requested through a link in a text message."),
    Actie("A3", "€2,400 to a new payee, at 23:10", "betaling", 2400, nieuwe_begunstigde=True, uur=23,
          context="Right after a call from someone claiming to be 'the security team'."),
)


def is_nacht(uur: int) -> bool:
    return uur >= 22 or uur < 7


def beslis(actie: Actie, mandaat: Mandaat, saldo: float, uitgaven_pm: float) -> dict:
    if (mandaat.blokkeer_nieuwe_begunstigde_nacht and actie.nieuwe_begunstigde and is_nacht(actie.uur)
            and actie.bedrag > mandaat.vraag_boven):
        besl, regel, waarom = GEBLOKKEERD, 4, "Large amount, new payee, at night. Kate is calling you."
    elif actie.soort == "overschrijving_spaargeld" and (saldo - actie.bedrag) < mandaat.buffer_maanden_min * uitgaven_pm:
        rest = round((saldo - actie.bedrag) / max(uitgaven_pm, 1), 1)
        besl, regel = GEBLOKKEERD, 1
        waarom = f"After this, only {rest} months of buffer left; your minimum is {mandaat.buffer_maanden_min}."
    elif actie.soort == "energie":
        if actie.besparing_per_jaar > mandaat.energie_auto_besparing:
            besl, regel = UITGEVOERD, 3
            waarom = f"Saving of €{actie.besparing_per_jaar:.0f} is above your limit of €{mandaat.energie_auto_besparing}."
        else:
            besl, regel, waarom = VRAAG, 3, "Saving too small to switch automatically."
    elif actie.bedrag > mandaat.vraag_boven:
        besl, regel, waarom = VRAAG, 2, f"€{actie.bedrag:,.0f} is above your limit of €{mandaat.vraag_boven}."
    else:
        besl, regel, waarom = UITGEVOERD, 2, f"Below your limit of €{mandaat.vraag_boven}."

    return {
        "actie": actie.id,
        "omschrijving": actie.omschrijving,
        "beslissing": besl,
        "regel": regel,
        "regeltekst": mandaat.regels()[regel - 1],
        "waarom": waarom,
        "mandaat": asdict(mandaat),
    }
