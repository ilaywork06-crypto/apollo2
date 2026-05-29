"""Shared pytest fixtures for all test layers."""

import pytest


# ---------------------------------------------------------------------------
# Fund dict factories
# ---------------------------------------------------------------------------


def make_fund(
    fund_id: str = "1001",
    fund_name: str = "Test Fund",
    hevra: str = "Test Co",
    sug: str = "תגמולים ואישית לפיצויים",
    risk_level: str = "medium",
    tsua_1: float = 10.0,
    tsua_3: float = 8.0,
    tsua_5: float = 7.0,
    sharpe: float = 1.5,
    equity_exposure: float = 50.0,
) -> dict:
    return {
        "ID": fund_id,
        "fund_name": fund_name,
        "hevra": hevra,
        "SUG": sug,
        "UCHLUSIYAT_YAAD": "כלל האוכלוסיה",
        "risk_level": risk_level,
        "tsua_mitztaberet_letkufa": tsua_1,
        "tsua_3": tsua_3,
        "tsua_5": tsua_5,
        "sharp_ribit_hasarot_sikun": sharpe,
        "equity_exposure": equity_exposure,
        "hitmahut_rashit": "N/A",
        "hitmahut_mishnit": "N/A",
        "num_hevra": "N/A",
    }


def make_mislaka(
    gemelnet_id: str = "1001",
    balance: float = 100_000.0,
    dmei_nihul_tzvira: float = 0.5,
    dmei_nihul_hafkada: float = 0.0,
    client_id: str = "123456789",
    seniority_date: str = "01/01/2020",
    tochnit_name: str = "Test Plan",
    yatzran_code: str = "Y001",
) -> dict:
    return {
        "GEMELNET_ID": gemelnet_id,
        "SHEM-TOCHNIT": tochnit_name,
        "TAARICH-HITZTARFUT-MUTZAR": seniority_date,
        "TOTAL-CHISACHON-MTZBR": balance,
        "SHEUR-DMEI-NIHUL-TZVIRA": dmei_nihul_tzvira,
        "SHEUR-DMEI-NIHUL-HAFKADA": dmei_nihul_hafkada,
        "KOD-MEZAHE-YATZRAN": yatzran_code,
        "MISPAR-ZIHUY-LAKOACH": client_id,
    }


def make_normalized_fund(
    fund_id: str = "1001",
    tsua_1_norm: float = 80.0,
    tsua_3_norm: float = 75.0,
    tsua_5_norm: float = 70.0,
    sharpe_norm: float = 85.0,
    **kwargs,
) -> dict:
    fund = make_fund(fund_id=fund_id, **kwargs)
    fund["tsua_mitztaberet_letkufa_normalized"] = tsua_1_norm
    fund["tsua_3_normalized"] = tsua_3_norm
    fund["tsua_5_normalized"] = tsua_5_norm
    fund["sharp_ribit_hasarot_sikun_normalized"] = sharpe_norm
    return fund


# ---------------------------------------------------------------------------
# Sample XML strings
# ---------------------------------------------------------------------------


MINIMAL_RISKS_MAP_XML = """\
<ROWSET>
  <Row>
    <SHM_SUG_NECHES>, חשיפה למניות</SHM_SUG_NECHES>
    <ID_KUPA>1001</ID_KUPA>
    <ACHUZ_SUG_NECHES>10.0</ACHUZ_SUG_NECHES>
  </Row>
  <Row>
    <SHM_SUG_NECHES>, חשיפה למניות</SHM_SUG_NECHES>
    <ID_KUPA>1002</ID_KUPA>
    <ACHUZ_SUG_NECHES>50.0</ACHUZ_SUG_NECHES>
  </Row>
  <Row>
    <SHM_SUG_NECHES>, חשיפה למניות</SHM_SUG_NECHES>
    <ID_KUPA>1003</ID_KUPA>
    <ACHUZ_SUG_NECHES>90.0</ACHUZ_SUG_NECHES>
  </Row>
  <Row>
    <SHM_SUG_NECHES>אג&quot;ח ממשלתיות</SHM_SUG_NECHES>
    <ID_KUPA>1004</ID_KUPA>
    <ACHUZ_SUG_NECHES>30.0</ACHUZ_SUG_NECHES>
  </Row>
</ROWSET>
"""

MINIMAL_FUNDS_XML = """\
<ROWSET>
  <Row>
    <UCHLUSIYAT_YAAD>כלל האוכלוסיה</UCHLUSIYAT_YAAD>
    <SUG_KUPA>תגמולים ואישית לפיצויים</SUG_KUPA>
    <ID>1001</ID>
    <SHM_KUPA>Fund Alpha</SHM_KUPA>
    <SHM_HEVRA_MENAHELET>Hevra A</SHM_HEVRA_MENAHELET>
    <HITMAHUT_RASHIT>N/A</HITMAHUT_RASHIT>
    <HITMAHUT_MISHNIT>N/A</HITMAHUT_MISHNIT>
    <NUM_HEVRA>1</NUM_HEVRA>
    <TSUA_MITZTABERET_LETKUFA>15.0</TSUA_MITZTABERET_LETKUFA>
    <TSUA_SHNATIT_MEMUZAAT_3_SHANIM>10.0</TSUA_SHNATIT_MEMUZAAT_3_SHANIM>
    <TSUA_SHNATIT_MEMUZAAT_5_SHANIM>9.0</TSUA_SHNATIT_MEMUZAAT_5_SHANIM>
    <SHARP_RIBIT_HASRAT_SIKUN>1.8</SHARP_RIBIT_HASRAT_SIKUN>
  </Row>
  <Row>
    <UCHLUSIYAT_YAAD>כלל האוכלוסיה</UCHLUSIYAT_YAAD>
    <SUG_KUPA>תגמולים ואישית לפיצויים</SUG_KUPA>
    <ID>1002</ID>
    <SHM_KUPA>Fund Beta</SHM_KUPA>
    <SHM_HEVRA_MENAHELET>Hevra B</SHM_HEVRA_MENAHELET>
    <HITMAHUT_RASHIT>N/A</HITMAHUT_RASHIT>
    <HITMAHUT_MISHNIT>N/A</HITMAHUT_MISHNIT>
    <NUM_HEVRA>2</NUM_HEVRA>
    <TSUA_MITZTABERET_LETKUFA>20.0</TSUA_MITZTABERET_LETKUFA>
    <TSUA_SHNATIT_MEMUZAAT_3_SHANIM>14.0</TSUA_SHNATIT_MEMUZAAT_3_SHANIM>
    <TSUA_SHNATIT_MEMUZAAT_5_SHANIM>12.0</TSUA_SHNATIT_MEMUZAAT_5_SHANIM>
    <SHARP_RIBIT_HASRAT_SIKUN>2.1</SHARP_RIBIT_HASRAT_SIKUN>
  </Row>
  <Row>
    <UCHLUSIYAT_YAAD>כלל האוכלוסיה</UCHLUSIYAT_YAAD>
    <SUG_KUPA>תגמולים ואישית לפיצויים</SUG_KUPA>
    <ID>1003</ID>
    <SHM_KUPA>Fund Gamma</SHM_KUPA>
    <SHM_HEVRA_MENAHELET>Hevra C</SHM_HEVRA_MENAHELET>
    <HITMAHUT_RASHIT>N/A</HITMAHUT_RASHIT>
    <HITMAHUT_MISHNIT>N/A</HITMAHUT_MISHNIT>
    <NUM_HEVRA>3</NUM_HEVRA>
    <TSUA_MITZTABERET_LETKUFA>8.0</TSUA_MITZTABERET_LETKUFA>
    <TSUA_SHNATIT_MEMUZAAT_3_SHANIM>6.0</TSUA_SHNATIT_MEMUZAAT_3_SHANIM>
    <TSUA_SHNATIT_MEMUZAAT_5_SHANIM>5.0</TSUA_SHNATIT_MEMUZAAT_5_SHANIM>
    <SHARP_RIBIT_HASRAT_SIKUN>0.9</SHARP_RIBIT_HASRAT_SIKUN>
  </Row>
  <Row>
    <UCHLUSIYAT_YAAD>פנסיה מקיפה</UCHLUSIYAT_YAAD>
    <SUG_KUPA>תגמולים ואישית לפיצויים</SUG_KUPA>
    <ID>9999</ID>
    <SHM_KUPA>Pension Special</SHM_KUPA>
    <SHM_HEVRA_MENAHELET>Special Co</SHM_HEVRA_MENAHELET>
    <HITMAHUT_RASHIT>N/A</HITMAHUT_RASHIT>
    <HITMAHUT_MISHNIT>N/A</HITMAHUT_MISHNIT>
    <NUM_HEVRA>9</NUM_HEVRA>
    <TSUA_MITZTABERET_LETKUFA>30.0</TSUA_MITZTABERET_LETKUFA>
    <TSUA_SHNATIT_MEMUZAAT_3_SHANIM>25.0</TSUA_SHNATIT_MEMUZAAT_3_SHANIM>
    <TSUA_SHNATIT_MEMUZAAT_5_SHANIM>22.0</TSUA_SHNATIT_MEMUZAAT_5_SHANIM>
    <SHARP_RIBIT_HASRAT_SIKUN>3.0</SHARP_RIBIT_HASRAT_SIKUN>
  </Row>
</ROWSET>
"""

MINIMAL_MISLAKA_XML = """\
<MislakaRoot>
  <YeshutLakoach>
    <MISPAR-ZIHUY-LAKOACH>987654321</MISPAR-ZIHUY-LAKOACH>
  </YeshutLakoach>
  <Mutzar>
    <KOD-MEZAHE-YATZRAN>TestYatzran</KOD-MEZAHE-YATZRAN>
    <HeshbonOPolisa>
      <SHEM-TOCHNIT>My Test Plan</SHEM-TOCHNIT>
      <TAARICH-HITZTARFUT-MUTZAR>15/03/2019</TAARICH-HITZTARFUT-MUTZAR>
      <PirteiTaktziv>
        <PerutMasluleiHashkaa>
          <SCHUM-TZVIRA-BAMASLUL>200000.0</SCHUM-TZVIRA-BAMASLUL>
          <KOD-MASLUL-HASHKAA>XX001001</KOD-MASLUL-HASHKAA>
          <SHEUR-DMEI-NIHUL-HISACHON>0.75</SHEUR-DMEI-NIHUL-HISACHON>
        </PerutMasluleiHashkaa>
      </PirteiTaktziv>
    </HeshbonOPolisa>
  </Mutzar>
</MislakaRoot>
"""

MISLAKA_TWO_TRACKS_XML = """\
<MislakaRoot>
  <YeshutLakoach>
    <MISPAR-ZIHUY-LAKOACH>111222333</MISPAR-ZIHUY-LAKOACH>
  </YeshutLakoach>
  <Mutzar>
    <KOD-MEZAHE-YATZRAN>MultiYatzran</KOD-MEZAHE-YATZRAN>
    <HeshbonOPolisa>
      <SHEM-TOCHNIT>Multi Track Plan</SHEM-TOCHNIT>
      <TAARICH-HITZTARFUT-MUTZAR>01/06/2018</TAARICH-HITZTARFUT-MUTZAR>
      <PirteiTaktziv>
        <PerutMasluleiHashkaa>
          <SCHUM-TZVIRA-BAMASLUL>50000.0</SCHUM-TZVIRA-BAMASLUL>
          <KOD-MASLUL-HASHKAA>XX001001</KOD-MASLUL-HASHKAA>
          <SHEUR-DMEI-NIHUL-HISACHON>0.5</SHEUR-DMEI-NIHUL-HISACHON>
        </PerutMasluleiHashkaa>
        <PerutMasluleiHashkaa>
          <SCHUM-TZVIRA-BAMASLUL>80000.0</SCHUM-TZVIRA-BAMASLUL>
          <KOD-MASLUL-HASHKAA>XX001002</KOD-MASLUL-HASHKAA>
          <SHEUR-DMEI-NIHUL-HISACHON>0.8</SHEUR-DMEI-NIHUL-HISACHON>
        </PerutMasluleiHashkaa>
      </PirteiTaktziv>
    </HeshbonOPolisa>
  </Mutzar>
</MislakaRoot>
"""
