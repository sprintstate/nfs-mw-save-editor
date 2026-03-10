from __future__ import annotations

from typing import Dict, Optional


def _sig(hex_bytes: str) -> bytes:
    return bytes.fromhex(hex_bytes)


CAR_SIGNATURES: Dict[bytes, str] = {
    _sig("BB D9 2A E3 BB D9 2A E3"): "Mercedes SLR McLaren",
    _sig("9E 57 65 01 9E 57 65 01"): "Corvette C6.R",
    _sig("7B 4B F6 F8 BF 42 7E 9B"): "Audi A4 Quattro",
    _sig("EA A5 C0 42 EA A5 C0 42"): "Ford GT",
    _sig("AF 2D C3 C1 C7 1A 47 A7"): "Dumptruck",
    _sig("33 C8 09 8E 33 C8 09 8E"): "Mazda RX-7",
    _sig("BB B5 00 A8 BB B5 00 A8"): "Mercedes SL 500",
    _sig("CF 82 E5 22 E4 8C 11 46"): "Corvette C6",
    _sig("4E 4A CC 23 F8 E0 DA 39"): "BMW M3 GTR (slow version)",
    _sig("AF 2D C3 C1 AE 75 E6 28"): "Cop SUV",
    _sig("92 99 86 C4 D4 3D 06 67"): "Porsche Carrera GT",
    _sig("DA A7 4D 3C DA A7 4D 3C"): "Porsche 911 Carrera S",
    _sig("AF 2D C3 C1 95 DC 49 69"): "Cop GTO",
    _sig("36 49 3D 31 36 49 3D 31"): "Lotus Elise",
    _sig("AF 2D C3 C1 D8 E0 EC 71"): "Civilcar Van",
    _sig("AF 2D C3 C1 F1 1A F0 7A"): "Taxi",
    _sig("7B C1 72 7B E5 14 C4 D5"): "Audi A3 Quattro",
    _sig("C8 8B 3A 19 C8 8B 3A 19"): "Audi TT Quattro",
    _sig("53 4B 05 79 53 4B 05 79"): "VW Golf GTI",
    _sig("BD 0B D7 A2 BD 0B D7 A2"): "Mitsubishi Eclipse",
    _sig("EB 67 18 EB EB 67 18 EB"): "Renault Clio V6",
    _sig("95 40 78 5A 95 40 78 5A"): "Chevrolet Cobalt SS",
    _sig("EB 77 CD C1 EB 77 CD C1"): "Lamborghini Murcielago",
    _sig("AF 2D C3 C1 49 39 3B 74"): "Civilcar Pickup",
    _sig("4E 4A CC 23 B3 5F 08 4E"): "BMW M3 GTR",
    _sig("2F AF 77 82 2F AF 77 82"): "Mercedes CLK 500",
    _sig("4D FD 93 9B 4D FD 93 9B"): "Ford Mustang GT",
    _sig("EB 5B 55 41 EB 5B 55 41"): "Porsche Cayman S",
    _sig("11 7A EE A6 11 7A EE A6"): "Fiat Punto",
    _sig("AF 2D C3 C1 F5 7E 66 70"): "Cop",
    _sig("20 65 18 DF 20 65 18 DF"): "Cadillac CTS",
    _sig("A1 E1 D3 D8 A1 E3 D3 D8"): "Vauxhall Monaro VXR",
    _sig("A1 F9 47 71 A1 F9 47 71"): "Mercedes SL65 AMG",
    _sig("6F F4 3E 9B 6F F4 3E 9B"): "Porsche 911 GT2",
    _sig("0B C4 2C 7B 0B C4 2C 7B"): "Lamborghini Gallardo",
    _sig("34 34 F1 66 34 34 F1 66"): "Toyota Supra",
    _sig("34 89 8C 19 0D 56 3B 5F"): "Subaru Impreza WRX STI",
    _sig("B6 FB EE CC B6 FB EE CC"): "Mitsubishi Lancer EVO VIII",
    _sig("AF 2D C3 C1 FA FF D9 51"): "Cementtruck",
    _sig("AF 2D C3 C1 64 5F DC F9"): "Ford Mustang GT?",
    _sig("C6 3D 48 AA C6 3D 48 AA"): "Pontiac GTO",
    _sig("08 D4 BE 6E 08 D4 BE 6E"): "Dodge Viper SRT10",
    _sig("19 45 94 90 19 45 94 90"): "Chevrolet Camaro SS",
    _sig("AF 2D C3 C1 4B C7 F2 C5"): "Pizza",
    _sig("6A 1C B6 A4 6A 1C B6 A4"): "Aston Martin DB9",
    _sig("37 44 33 D6 37 44 33 D6"): "Mazda RX-8",
    _sig("A6 FE C2 81 3F 08 88 CD"): "BMW M3 Street Version",
    _sig("B0 2F FF 5B B0 2F FF 5B"): "Lexus IS300",
    _sig("8D 5B 7D D2 8D 5B 7D D2"): "Porsche 911 Turbo S",
    _sig("AF 2D C3 C1 0C 07 6C 8F"): "Cop Corvette",
}


def resolve_car_name(signature: bytes) -> Optional[str]:
    return CAR_SIGNATURES.get(bytes(signature))


def format_signature(signature: bytes) -> str:
    return bytes(signature).hex(" ").upper()
