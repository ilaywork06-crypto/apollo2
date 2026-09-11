"""Property: whatever tracks we write into a Mislaka file, the parser reads the same values back."""

from hypothesis import given
from hypothesis import strategies as st

from src.parsers.mislaka.parser import parse_mislaka_file

hebrew_words = st.text(alphabet="אבגדהוזחטיכלמנסעפצקרשת", min_size=1, max_size=8)
tracks = st.lists(
    st.tuples(
        st.integers(1, 999_999),                          # fund code
        st.integers(100, 500_000_000).map(lambda n: n / 100),  # balance >= 1 NIS, in agorot
        st.integers(13, 250).map(lambda n: n / 100),      # accumulation fee, above the fallback threshold
    ),
    min_size=1,
    max_size=5,
)


def _file(client_id, first, last, rows, encoding):
    body = "".join(
        f"<PerutMasluleiHashkaa><SCHUM-TZVIRA-BAMASLUL>{balance}</SCHUM-TZVIRA-BAMASLUL>"
        f"<KOD-MASLUL-HASHKAA>512267592{code:06d}</KOD-MASLUL-HASHKAA>"
        f"<SHEUR-DMEI-NIHUL-HISACHON>{fee}</SHEUR-DMEI-NIHUL-HISACHON></PerutMasluleiHashkaa>"
        for code, balance, fee in rows
    )
    return (
        f'<?xml version="1.0" encoding="{encoding}"?>'
        f"<MislakaRoot><YeshutLakoach><MISPAR-ZIHUY-LAKOACH>{client_id}</MISPAR-ZIHUY-LAKOACH>"
        f"<SHEM-PRATI>{first}</SHEM-PRATI><SHEM-MISHPACHA>{last}</SHEM-MISHPACHA></YeshutLakoach>"
        f"<Mutzar><KOD-MEZAHE-YATZRAN>Y</KOD-MEZAHE-YATZRAN><HeshbonOPolisa>"
        f"<SHEM-TOCHNIT>P</SHEM-TOCHNIT><TAARICH-HITZTARFUT-MUTZAR>20200101</TAARICH-HITZTARFUT-MUTZAR>"
        f"<PirteiTaktziv>{body}</PirteiTaktziv></HeshbonOPolisa></Mutzar></MislakaRoot>"
    )


@given(st.from_regex(r"\A0?[1-9][0-9]{7}\Z"), hebrew_words, hebrew_words, tracks,
       st.sampled_from(["UTF-8", "windows-1255"]), st.booleans())
def test_tracks_survive_a_round_trip(client_id, first, last, rows, encoding, as_bytes):
    text = _file(client_id, first, last, rows, encoding)
    content = text.encode("cp1255" if encoding == "windows-1255" else "utf-8") if as_bytes else text
    records = parse_mislaka_file(content)
    assert [(r["GEMELNET_ID"], r["TOTAL-CHISACHON-MTZBR"], r["SHEUR-DMEI-NIHUL-TZVIRA"]) for r in records] == [
        (str(code), balance, fee) for code, balance, fee in rows
    ]
    assert {(r["MISPAR-ZIHUY-LAKOACH"], r["SHEM-LAKOACH"]) for r in records} == {(client_id, f"{first} {last}")}
