"""Het Levensmandaat: de klant schrijft de regels, de agent handelt erbinnen.

beslis() is puur: dezelfde actie en hetzelfde mandaat geven altijd dezelfde
beslissing. Het vastleggen (tijd, hashketen) gebeurt in engine.audit.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

UITGEVOERD = "Uitgevoerd"
VRAAG = "Vraagt eerst toestemming"
GEBLOKKEERD = "Geblokkeerd"
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
            f"Mijn noodbuffer zakt nooit onder {self.buffer_maanden_min} maanden uitgaven.",
            f"Alles boven €{self.vraag_boven} vraag je eerst.",
            f"Stap over naar goedkopere energie als ik meer dan €{self.energie_auto_besparing} per jaar bespaar.",
        ]
        if self.blokkeer_nieuwe_begunstigde_nacht:
            r.append("Een groot bedrag 's nachts naar een nieuwe begunstigde: altijd blokkeren en mij bellen.")
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
    Actie("A1", "Energie-agent biedt een contract aan dat €140 per jaar goedkoper is", "energie", 0, besparing_per_jaar=140,
          context="Onderhandeld door je agent met de agent van de leverancier."),
    Actie("A2", "Betaling van €600 aan Garage Janssens (bekende begunstigde)", "betaling", 600, uur=10),
    Actie("A3", "Overschrijving van €2.400 naar een nieuwe begunstigde, om 23u10", "betaling", 2400,
          nieuwe_begunstigde=True, uur=23, context="Kort na een telefoontje van iemand die zei van 'de veiligheidsdienst' te zijn."),
    Actie("A4", "€35.000 van je spaarrekening naar een beleggingsrekening", "overschrijving_spaargeld", 35_000, uur=11),
)


def is_nacht(uur: int) -> bool:
    return uur >= 22 or uur < 7


def beslis(actie: Actie, mandaat: Mandaat, saldo: float, uitgaven_pm: float) -> dict:
    if (mandaat.blokkeer_nieuwe_begunstigde_nacht and actie.nieuwe_begunstigde and is_nacht(actie.uur)
            and actie.bedrag > mandaat.vraag_boven):
        besl, regel, waarom = GEBLOKKEERD, 4, "Groot bedrag, nieuwe begunstigde, 's nachts. Kate belt je om te checken."
    elif actie.soort == "overschrijving_spaargeld" and (saldo - actie.bedrag) < mandaat.buffer_maanden_min * uitgaven_pm:
        rest = round((saldo - actie.bedrag) / max(uitgaven_pm, 1), 1)
        besl, regel = GEBLOKKEERD, 1
        waarom = f"Na deze actie heb je nog maar {rest} maanden buffer; je minimum is {mandaat.buffer_maanden_min}."
    elif actie.soort == "energie":
        if actie.besparing_per_jaar > mandaat.energie_auto_besparing:
            besl, regel = UITGEVOERD, 3
            waarom = f"Besparing €{actie.besparing_per_jaar:.0f} is meer dan je grens van €{mandaat.energie_auto_besparing}."
        else:
            besl, regel, waarom = VRAAG, 3, "Besparing is te klein om automatisch over te stappen."
    elif actie.bedrag > mandaat.vraag_boven:
        besl, regel, waarom = VRAAG, 2, f"€{actie.bedrag:,.0f} is meer dan je grens van €{mandaat.vraag_boven}.".replace(",", ".")
    else:
        besl, regel, waarom = UITGEVOERD, 2, f"Onder je grens van €{mandaat.vraag_boven}."

    return {
        "actie": actie.id,
        "omschrijving": actie.omschrijving,
        "beslissing": besl,
        "regel": regel,
        "regeltekst": mandaat.regels()[regel - 1],
        "waarom": waarom,
        "mandaat": asdict(mandaat),
    }
