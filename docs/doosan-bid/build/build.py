import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter as L

OUT = "/home/user/MEMORY/docs/doosan-bid/두산퓨얼셀_Cathode_사업성분석_통합모델.xlsx"
wb = openpyxl.Workbook(); wb.remove(wb.active)
YRS = list(range(2027, 2034)); YC = {y: L(4 + i) for i, y in enumerate(YRS)}
FIRST, LAST = YC[2027], YC[2033]
HDR_FILL = PatternFill("solid", fgColor="1F3864"); HDR_FONT = Font(bold=True, color="FFFFFF")
SEC_FILL = PatternFill("solid", fgColor="D9E1F2"); INP_FILL = PatternFill("solid", fgColor="FFF2CC")
INP_FONT = Font(color="0000FF"); TOT_FILL = PatternFill("solid", fgColor="F2F2F2")
WARN_FONT = Font(color="C00000", bold=True)
thin = Side(style="thin", color="BFBFBF"); BOX = Border(top=thin, bottom=thin, left=thin, right=thin)
W = "#,##0;[Red]△#,##0;-"; W1 = "#,##0.0;[Red]△#,##0.0;-"; W2 = "#,##0.00;[Red]△#,##0.00;-"; W4="0.0000"
P = "0.0%;[Red]△0.0%;-"

def sh(name, title, widths=None):
    ws = wb.create_sheet(name)
    ws["B1"] = title; ws["B1"].font = Font(bold=True, size=14)
    ws.column_dimensions["A"].width = 2; ws.column_dimensions["B"].width = 26; ws.column_dimensions["C"].width = 22
    for c in "DEFGHIJ": ws.column_dimensions[c].width = 15
    ws.column_dimensions["K"].width = 14; ws.column_dimensions["L"].width = 14; ws.column_dimensions["M"].width = 50
    if widths:
        for k, v in widths.items(): ws.column_dimensions[k].width = v
    ws.sheet_view.showGridLines = False
    return ws

def cell(ws, ref, v, fmt=None, inp=False, bold=False, fill=None, font=None, wrap=False):
    c = ws[ref]; c.value = v
    if fmt: c.number_format = fmt
    if inp: c.fill = INP_FILL; c.font = INP_FONT
    if bold: c.font = Font(bold=True, color=c.font.color.rgb if c.font and c.font.color and isinstance(c.font.color.rgb,str) else None)
    if fill: c.fill = fill
    if font: c.font = font
    if wrap: c.alignment = Alignment(wrap_text=True, vertical="top")
    c.border = BOX
    return c

def yhdr(ws, r, b="구분", c="세부", extra=("기준1", "기준2", "비고")):
    for col, v in zip(["B", "C"] + [YC[y] for y in YRS] + ["K", "L", "M"], [b, c] + [y for y in YRS] + list(extra)):
        x = ws[f"{col}{r}"]; x.value = v; x.fill = HDR_FILL; x.font = HDR_FONT; x.alignment = Alignment(horizontal="center"); x.border = BOX

def sec(ws, r, text, span="M"):
    ws[f"B{r}"] = text; ws[f"B{r}"].font = Font(bold=True, size=11)
    for col in range(2, openpyxl.utils.column_index_from_string(span) + 1):
        ws.cell(r, col).fill = SEC_FILL

def yrow(ws, r, b, c, func, fmt=W, k=None, l=None, m=None, inp=False, tot=False, kfmt=None, lfmt=None):
    cell(ws, f"B{r}", b); cell(ws, f"C{r}", c)
    for i, y in enumerate(YRS):
        col = YC[y]; prev = YC[y - 1] if y > 2027 else None
        v = func(y, col, prev) if callable(func) else (func[i] if isinstance(func, (list, tuple)) else func)
        x = cell(ws, f"{col}{r}", v, fmt, inp=inp)
        if tot: x.fill = TOT_FILL; x.font = Font(bold=True)
    if k is not None: cell(ws, f"K{r}", k, kfmt, inp=isinstance(k, (int, float)) and not isinstance(k, bool))
    if l is not None: cell(ws, f"L{r}", l, lfmt)
    if m is not None: cell(ws, f"M{r}", m, wrap=False)
    if tot:
        ws[f"B{r}"].font = Font(bold=True); ws[f"B{r}"].fill = TOT_FILL; ws[f"C{r}"].fill = TOT_FILL

def ref(s, c, r, abs_=False):
    return f"'{s}'!${c}${r}" if abs_ else f"'{s}'!{c}{r}"

# =============================== 01 가정 ===============================
S1 = "01_가정"; ws = sh(S1, "01. 기본 가정 (입력값) — 파란 글씨·노란 셀만 수정", {"B": 34, "C": 16, "D": 12, "E": 70})
for col, v in zip("BCDE", ["항목", "값", "단위", "비고 / 출처"]):
    x = ws[f"{col}3"]; x.value = v; x.fill = HDR_FILL; x.font = HDR_FONT; x.border = BOX
R = {}
row = [4]
def inp(key, label, val, unit="", note="", fmt=None, formula=False):
    r = row[0]
    cell(ws, f"B{r}", label); cell(ws, f"C{r}", val, fmt, inp=not formula); cell(ws, f"D{r}", unit); cell(ws, f"E{r}", note)
    R[key] = f"'{S1}'!$C${r}"; row[0] += 1
def sec1(t):
    r = row[0]; sec(ws, r, t, "E"); row[0] += 1
sec1("1. 물동·판가")
inp("vol", "두산퓨얼셀 물량 (연간)", 1320, "kg/년", "#3 물동시나리오: 2027~2033 동일, LT 반영 100%", W)
inp("share", "LT 반영률 (M/S)", 1.0, "", "#3", P)
inp("cut", "판가 인하율", 0.02, "/년", "#2·#3: 단가인하율 2%", P)
inp("fx", "환율 (가공비 환산)", 1480, "원/$", "#1", W)
inp("proc_usd", "두산퓨얼셀 제시 가공비", 0.9, "$/g", "#1 요청사항: 목표 Cathode $0.8~0.9/g", W2)
inp("proc", "제시 가공비 (원화)", f"=C{row[0]-2}*C{row[0]-1}", "원/g", "환율 × $/g → 판가 = 재료비 원단위 + 가공비", W, True)
sec1("2. 상승률")
inp("infl", "물가상승률", 0.05, "/년", "재료비·유틸·소모품·포장·운반", P)
inp("wage", "임금상승률", 0.06, "/년", "#8", P)
inp("base", "상승률 기준연도", 2026, "년", "원본: 2027년 값 = 기준단가 × 1.05¹ (기준 2026). ※ 원 단가는 '24·'25년 기준 → 검토사항 참고", "0")
sec1("3. 백금·원재료 단가")
inp("pt_usd", "백금 가격", 1000, "$/Toz", "#4: 25년 사업계획", W)
inp("pt_fx", "백금 환율", 1370, "원/$", "#4", W)
inp("toz", "1 Troy oz", 31.1035, "g", "", W4)
inp("pt", "백금 단가", f"=C{row[0]-3}*C{row[0]-2}/C{row[0]-1}", "원/g", "약 44,046원/g", W, True)
inp("c_cat", "Cathode 카본 단가", 1000, "원/g", "#4: LT소재 구매 기준 1kg/100만원", W)
inp("c_an", "Anode 카본 단가", 98, "원/g", "#4: CABOT 열처리 전", W)
inp("cr_p", "Cr Chloride 전구체 구매가", 90000, "원/kg", "#4: 동문케미칼", W)
inp("cr_c", "Cr 함량", 0.2224, "", "", P)
inp("cr", "크롬 단가", f"=C{row[0]-2}/1000/C{row[0]-1}", "원/g", "약 405원/g", W1, True)
inp("co_p", "Co Chloride 전구체 구매가", 33000, "원/kg", "#4: 동문케미칼", W)
inp("co_c", "Co 함량", 0.2476, "", "", P)
inp("co", "코발트 단가", f"=C{row[0]-2}/1000/C{row[0]-1}", "원/g", "약 133원/g", W1, True)
sec1("4. 공정·유틸리티")
inp("b_proc", "촉매 공정 Batch 크기", 4, "kg/batch", "#1·#9·#18 (합성/열처리)", W1)
inp("b_prec", "전구체 Batch 크기", 5, "kg/batch", "#9(2028~)·#17: 5kg/Batch, 100ℓ 반응기", W1)
inp("b_anal", "분석 기준 Batch 크기", 4, "kg/batch", "#11: 촉매 4,000g/Batch 생산시 1회 분석 (원본 #9 2028~는 3.6kg로 계산)", W1)
inp("b_pack", "포장 기준 Batch 크기", 3600, "g/batch", "#12 원본값 (다른 시트 4,000g과 상이 → 검토사항)", W)
inp("elec", "전기요금", 190, "원/kWh", "#9: 남동공장 '25년", W)
inp("water", "순수 단가", 7.7, "원/kg", "#9", W1)
inp("waste", "일반폐수 단가", 150, "원/kg", "#9", W1)
inp("wmul", "순수 사용 배수", 50, "배/kg", "#9: 물량 1kg당 순수 50kg", W)
inp("wash", "세척 횟수 (Cathode)", 7, "회", "#9", W)
sec1("5. 투자·재무")
inp("inv_y", "설비 투자연도", 2027, "년", "#7·#14 (※ #10은 2026년 표기)", "0")
inp("dep_n", "설비 감가상각 연수", 5, "년", "#2: 설비 5년, 건물 20년", W)
inp("rep", "수선비율 (설비가액 대비)", 0.02, "", "#10: 설비가액의 2% (※ #2 비고 5%는 오기)", P)
inp("eq_rate", "설비금리", 0.05, "", "#10 (원본 영업외비용 합계에는 미포함)", P)
inp("tax", "법인세율", 0.242, "", "#15: 경상이익의 24.2%", P)
inp("comm", "판매 공통경비율 (영업 인건비 대비)", 0.5, "", "#10 역산: 공통경비 = 영업 인건비 × 50%", P)
inp("col_m", "매출 수금기간", 1, "개월", "#15: 수금 30일", W)
inp("inv_m", "재고 보유기간", 1, "개월", "#15: 재고 30일, 매입 당일결제", W)
sec1("6. 판관비·기타")
inp("trips", "운반 횟수", 48, "회/년", "#13: 월 4회, 1톤 차량", W)
inp("trip_c", "운반 1회 비용", 330000, "원/회", "#13: 기사 인건비·유류비 포함", W)
inp("edu_o", "교육훈련비 (사무직)", 692000, "원/인·년", "#8", W)
inp("edu_t", "교육훈련비 (기능직)", 70000, "원/인·년", "#8", W)
inp("it", "전산유지비 (사무직)", 420000, "원/인·년", "#8", W)
inp("out_n", "용역 인원", 3, "명", "#8 지급수수료 (원본 손익 미반영 → 21_보정손익)", W1)
inp("out_c", "용역 단가 (기준연도)", 42000000, "원/인·년", "#8 역산: 133,560,000 / 3명 / 1.06", W)
sec1("7. LT소재 비교 (#1)")
inp("lt_amt", "LT소재 공급금액", 1200000000, "원", "#1 메모: 110kg - 공급가 12억", W)
inp("lt_kg", "LT소재 공급량", 110, "kg", "", W)
inp("tgt_lo", "목표 가공비 하한 (Cathode)", 0.8, "$/g", "#1 요청사항", W2)
inp("tgt_hi", "목표 가공비 상한 (Cathode)", 0.9, "$/g", "", W2)
inp("tgt_an", "목표 가공비 (Anode)", 0.6, "$/g", "", W2)
inp("tol", "원본검증 허용오차", 1000, "원", "23_원본검증 판정 기준", W)
ws.freeze_panes = "B4"

# fixed row plan for 02
S2 = "02_물동시나리오"; R2 = dict(price=13, an_g=21, sup_g=23, kg=25, sales=31, va=34, mat=38, disc=39)
# =============================== 03 재료비 ===============================
S3 = "03_재료비"; ws = sh(S3, "03. 재료비 산출 근거 (#4)", {"N": 12, "O": 10})
sec(ws, 3, "1) 원단위 재료비 (원/g 촉매, 물가 반영) — K: 반영 소요량(g/g), L: 기준단가(원/g)")
yhdr(ws, 4, "구분", "원재료", ("소요량(g)", "기준단가", "비고"))
cell(ws, "N4", "기본소요", fill=HDR_FILL, font=HDR_FONT); cell(ws, "O4", "Loss", fill=HDR_FILL, font=HDR_FONT)
def matrow(r, b, c, base, loss, price, note, k_formula=None):
    cell(ws, f"N{r}", base, W4 if base < 1 else W, inp=True); cell(ws, f"O{r}", loss, P, inp=True)
    yrow(ws, r, b, c, lambda y, col, p: f"=$K{r}*$L{r}*(1+{R['infl']})^({col}$4-{R['base']})", W1,
         k=f"=N{r}*(1+O{r})", l=price, m=note, kfmt="0.00000", lfmt=W1)
matrow(5, "Cathode 16.7% PtCrCo/C", "백금 (Pt 12%)", 0.118, 0.02, f"={R['pt']}", "#4 표시 0.120 = 0.118×1.02 (비고 '0.12g+2%'와 상이 → 검토사항)")
matrow(6, "", "크롬 (Cr 2.7%)", 0.014, 0, f"={R['cr']}", "#4 셀값 0.014 (비고 '0.027g+25%'와 상이)")
matrow(7, "", "코발트 (Co 2%)", 0.021, 0, f"={R['co']}", "#4 셀값 0.021 (비고 '0.02g+25%'와 상이)")
matrow(8, "", "카본 블랙", 0.8672738, 0, f"={R['c_cat']}", "#4 표시 0.867 — 원본 합계(6,486.03원)에 맞춰 소수점 역산")
yrow(ws, 9, "Cathode 소계", "원/g", lambda y, c, p: f"=SUM({c}5:{c}8)", W1, tot=True)
matrow(11, "Anode 10% Pt/C (참고)", "백금 (Pt 10%)", 0.1, 0.02, f"={R['pt']}", "#4: 0.1g + Loss 2%")
matrow(12, "", "카본 블랙", 0.9, 0.002, f"={R['c_an']}", "#4: 0.9g + Loss 0.2%")
yrow(ws, 13, "Anode 소계", "원/g", lambda y, c, p: f"=SUM({c}11:{c}12)", W1, tot=True)
sec(ws, 15, "2) 물동량 반영 원재료비 (원)")
yhdr(ws, 16, "구분", "", ("", "", "비고"))
yrow(ws, 17, "16.7% PtCrCo/C 재료비", "원", lambda y, c, p: f"={c}9*'{S2}'!{c}{R2['sup_g']}", W, m="원단위 × LT 공급량(g). ※ 원본 비고 '제조로스 2% 반영'은 실제 미적용 → 21_보정손익 양품률 항목")
yrow(ws, 18, "10% Pt/C 재료비", "원", lambda y, c, p: f"={c}13*'{S2}'!{c}{R2['an_g']}", W)
yrow(ws, 19, "재료비 합계", "원", lambda y, c, p: f"={c}17+{c}18", W, tot=True)
ws.freeze_panes = "D5"
R3 = dict(cat=9, an=13, total=19)

# =============================== 02 물동시나리오 ===============================
ws = sh(S2, "02. 물동 시나리오 (#3 요약본 2.)", {"B": 16, "C": 30, "K": 12})
PTC = "PtCrCo16.7% (Pt 12%·Cr 2.7%·Co 2%)"
sec(ws, 3, "1) 고객사 제시 물량 (촉매)  (단위: g)")
yhdr(ws, 4, "고객", "구분", ("LT 반영", "", "산출근거"))
yrow(ws, 5, "두산퓨얼셀", "Pt10% — 두산퓨얼셀 제시 물량", 0, W, inp=True)
yrow(ws, 6, "", "Pt10% — LT 반영", lambda y, c, p: f"={c}5*$K$6", W, k=1.0, kfmt=P, m="제시 물량의 100% 반영")
yrow(ws, 7, "", PTC + " — 두산퓨얼셀 제시 물량", lambda y, c, p: f"={R['vol']}*1000", W, m="01_가정 물량(kg) × 1,000. 연도별로 다르면 이 행에 직접 입력")
yrow(ws, 8, "", PTC + " — LT 반영", lambda y, c, p: f"={c}7*$K$8", W, k=f"={R['share']}", kfmt=P, m="제시 물량의 100% 반영", tot=True)
sec(ws, 10, "2) 판가  (단위: 원/g)")
yhdr(ws, 11, "고객", "구분", ("", "", "산출근거"))
cell(ws, "B12", "두산퓨얼셀"); cell(ws, "B13", "임가공비 = 판가")
yrow(ws, 12, "두산퓨얼셀", "Pt10%", 0, W, inp=True, m="가공비 및 백금 가격 적용 (Anode 판가 미정)")
yrow(ws, 13, "임가공비 = 판가", "PtCrCo16.7%", lambda y, c, p: (f"='{S3}'!{c}{R3['cat']}+{R['proc']}" if y == 2027 else f"={p}13*(1-{R['cut']})"), W,
     m="가공비 및 백금 가격 적용: 2027 = 재료비 원단위 + 제시 가공비, 이후 연 2% 인하", tot=True)
sec(ws, 15, "3) 시장규모  (단위: g)")
yhdr(ws, 16, "구분", "", ("", "", "산출근거"))
yrow(ws, 17, "고객사 총 소요량 (g)", "Pt10%", lambda y, c, p: f"={c}5", W)
yrow(ws, 18, "", "PtCrCo16.7%", lambda y, c, p: f"={c}7", W)
yrow(ws, 19, "", "소계 (g)", lambda y, c, p: f"={c}17+{c}18", W, tot=True)
yrow(ws, 20, "LT 공급량 (%, g)", "LT M/S (%) — Pt10%", lambda y, c, p: f"=$K$6", P)
yrow(ws, 21, "", "공급량 (g) — Pt10%", lambda y, c, p: f"={c}17*{c}20", W)
yrow(ws, 22, "", "LT M/S (%) — PtCrCo16.7%", lambda y, c, p: f"=$K$8", P)
yrow(ws, 23, "", "공급량 (g) — PtCrCo16.7%", lambda y, c, p: f"={c}18*{c}22", W)
yrow(ws, 24, "합계 (g)", "", lambda y, c, p: f"={c}21+{c}23", W, tot=True)
yrow(ws, 25, "[참고] Cathode 공급량", "kg", lambda y, c, p: f"={c}23/1000", W1, m="전력·Capa·용수 등 kg 기준 계산에 연결")
sec(ws, 27, "4) 매출액 및 부가가치  (단위: 원 — 원본 '백만원' 표기는 오기)")
yhdr(ws, 28, "구분", "", ("", "", "산출근거"))
yrow(ws, 29, "매출액", "Pt10% Anode", lambda y, c, p: f"={c}12*{c}21", W)
yrow(ws, 30, "", "PtCrCo16.7% Cathode", lambda y, c, p: f"={c}13*{c}23", W)
yrow(ws, 31, "", "합계 (원)", lambda y, c, p: f"={c}29+{c}30", W, tot=True, m="판가 × LT 공급량")
yrow(ws, 32, "부가가치", "Pt10% Anode", lambda y, c, p: f"={c}29-'{S3}'!{c}18", W)
yrow(ws, 33, "", "PtCrCo16.7% Cathode", lambda y, c, p: f"={c}30-'{S3}'!{c}17", W)
yrow(ws, 34, "", "합계 (원)", lambda y, c, p: f"={c}32+{c}33", W, tot=True, m="매출액 − 재료비")
yrow(ws, 35, "부가가치율", "", lambda y, c, p: f"=IF({c}31=0,0,{c}34/{c}31)", P)
sec(ws, 37, "[참고] 연결용")
yrow(ws, 38, "재료비 합계", "원", lambda y, c, p: f"='{S3}'!{c}{R3['total']}", W, m="03_재료비")
yrow(ws, 39, "판가 할인계수", "(1−인하율)^n", lambda y, c, p: f"=(1-{R['cut']})^({c}4-2027)", W4, m="20_입찰시뮬 가공비 민감도 계산용")
ws.freeze_panes = "D5"

# =============================== 04 소모품비 ===============================
S4 = "04_소모품비"; ws = sh(S4, "04. 소모품비 산출 근거 (#11)")
sec(ws, 3, "1) 소모품 단위별 단가")
for col, v in zip("BCDEFM", ["공정", "품목", "구매금액(원)", "구매수량", "단가", "비고"]):
    cell(ws, f"{col}4", v, fill=HDR_FILL, font=HDR_FONT)
prices = [("전구체 제조", "HCl", 15000, 200000, "원/g", "200kg/15,000원"),
          ("전구체 제조", "KOH", 35600, 25000, "원/g", "25kg/35,600원 (각주 '수산화칼슘'은 오기 → 수산화칼륨)"),
          ("전구체 제조", "HNO3 (65%)", 45000, 25000, "원/g", "25kg/45,000원"),
          ("전구체 제조", "5C 필터", 102960, 100, "원/장", "100장/102,960원"),
          ("촉매 제조", "에탄올", 70100, 14202, "원/g", "14,202g/70,100원"),
          ("촉매 제조", "순수", 7.7, 1000, "원/g", "1,000g/7.7원"),
          ("촉매 제조", "MEA", 8100, 1000, "원/g", "1,000g/8,100원"),
          ("카본전처리", "E.G", 2935000, 1000000, "원/g", "1,000kg/2,935,000원"),
          ("산처리", "HNO3 (9%)", 145000, 25000, "원/g", "25kg/145,000원 (원본 계산에는 미사용)"),
          ("여과", "PTFE 필터", 3900000, 100, "원/장", "100장/3,900,000원"),
          ("GAS", "수소", 100000, 3525, "원/ℓ", "47ℓ·100기압·압축손실25% → 3,525ℓ / 100,000원"),
          ("GAS", "질소", 0.26, 1, "원/ℓ", ""),
          ("GAS", "산소", 120000, 3525, "원/ℓ", "3,525ℓ / 120,000원")]
PR = {}
for i, (a, b, amt, q, u, note) in enumerate(prices):
    r = 5 + i
    cell(ws, f"B{r}", a); cell(ws, f"C{r}", b); cell(ws, f"D{r}", amt, W1 if amt < 10 else W, inp=True); cell(ws, f"E{r}", q, W, inp=True)
    cell(ws, f"F{r}", f"=D{r}/E{r}", "#,##0.0000"); cell(ws, f"M{r}", f"[{u}] {note}")
    PR[b] = f"$F${r}"
sec(ws, 19, "2) Cathode 16.7% PtCrCo/C 소모품비 (원/g 촉매, 물가 반영) — K: 소요량(촉매 1g당), L: 단가")
yhdr(ws, 20, "공정", "품목", ("소요량", "단가", "소요량 근거"))
use = [("전구체 제조", "KOH", "=0.12*4", "KOH", "백금 1g당 KOH 4g"),
       ("전구체 제조", "HNO3 (65%)", "=0.12*3.16", "HNO3 (65%)", "백금 1g당 HNO3 3.16g"),
       ("전구체 제조", "5C 필터", "=2/5000*0.12", "5C 필터", "백금 5,000g/Batch당 2장"),
       ("촉매 제조", "순수", 1.135, "순수", "촉매 1g당 1.135g"),
       ("촉매 제조", "MEA", 0.1127145, "MEA", "표시 0.1127 (백금 1g당 0.943g) — 원본 합계에 맞춰 소수점 역산"),
       ("산처리", "HNO3 (65% 단가 적용)", 4.9225, "HNO3 (65%)", "원본: 65% 단가 적용 (9% 단가 적용시 → 21_보정손익)"),
       ("여과", "PTFE 필터", "=1/4000", "PTFE 필터", "4,000g/Batch당 1장"),
       ("GAS (생산)", "수소", "=6000/4000", "수소", "열처리 4,000g/Batch당 6,000ℓ"),
       ("GAS (생산)", "질소", "=50*4/4000", "질소", "50ℓ × 4회 / Batch"),
       ("GAS (분석)", "수소", "=3525/25/4000", "수소", "Batch당 1회 분석, 25회에 1통"),
       ("GAS (분석)", "산소", "=3525/8/4000", "산소", "Batch당 1회 분석, 8회에 1통")]
for i, (a, b, q, pk, note) in enumerate(use):
    r = 21 + i
    yrow(ws, r, a, b, lambda y, c, p, r=r: f"=$K{r}*$L{r}*(1+{R['infl']})^({c}$20-{R['base']})", W2,
         k=q, l=f"={PR[pk]}", m=note, kfmt="0.000000", lfmt="#,##0.0000")
    ws[f"K{r}"].fill = INP_FILL; ws[f"K{r}"].font = INP_FONT
R4_acid = 26
yrow(ws, 32, "Cathode 소계", "원/g", lambda y, c, p: f"=SUM({c}21:{c}31)", W2, tot=True)
sec(ws, 34, "3) 물동량 반영 소모품비 (원)")
yhdr(ws, 35, "구분", "", ("", "", ""))
yrow(ws, 36, "16.7% PtCrCo/C 소모품비", "원", lambda y, c, p: f"={c}32*'{S2}'!{c}{R2['sup_g']}", W, tot=True)
cell(ws, "M36", "Anode(10% Pt/C) 소모품 22.26원/g(2027)은 물량 0으로 생략")
ws.freeze_panes = "D5"
R4 = dict(total=36, acid=R4_acid)

# =============================== 05 포장비 ===============================
S5 = "05_포장비"; ws = sh(S5, "05. 포장비 산출 근거 (#12)")
yhdr(ws, 4, "구분", "품목", ("소요(개/g)", "단가(원/개)", "비고"))
yrow(ws, 5, "포장", "포장용기", lambda y, c, p: f"=$K5*$L5*(1+{R['infl']})^({c}$4-{R['base']})", W2, k=f"=2/{R['b_pack']}", l=25000, m="Batch당 2개", kfmt="0.000000")
yrow(ws, 6, "포장", "포장박스", lambda y, c, p: f"=$K6*$L6*(1+{R['infl']})^({c}$4-{R['base']})", W2, k=f"=1/{R['b_pack']}", l=2000, m="Batch당 1개", kfmt="0.000000")
for r in (5, 6): ws[f"L{r}"].fill = INP_FILL; ws[f"L{r}"].font = INP_FONT; ws[f"L{r}"].number_format = W
yrow(ws, 7, "합계", "원/g", lambda y, c, p: f"=SUM({c}5:{c}6)", W2, tot=True)
yrow(ws, 9, "16.7% PtCrCo/C 포장비", "원", lambda y, c, p: f"={c}7*'{S2}'!{c}{R2['sup_g']}", W, tot=True, m="원본은 3,600g/Batch 기준 (01_가정에서 변경 가능)")
R5 = dict(total=9)

# =============================== 06 운반비 ===============================
S6 = "06_운반비"; ws = sh(S6, "06. 운반비 산출 근거 (#13)")
yhdr(ws, 4)
yrow(ws, 5, "운반 횟수", "회/년", lambda y, c, p: f"={R['trips']}", W)
yrow(ws, 6, "운반 단가", "원/회", lambda y, c, p: f"={R['trip_c']}*(1+{R['infl']})^({c}$4-{R['base']})", W)
yrow(ws, 7, "16.7% PtCrCo/C 운반비", "원/년", lambda y, c, p: f"={c}5*{c}6", W, tot=True, m="판매비 '기타비용(운반비 포함)'으로 연결. 원본 '년간 운반비' 단위 '원/회'는 오기(원/년)")
yrow(ws, 8, "촉매 1g당 운반비", "원/g", lambda y, c, p: f"=IF('{S2}'!{c}{R2['sup_g']}=0,0,{c}7/'{S2}'!{c}{R2['sup_g']})", W2)
R6 = dict(total=7)

# =============================== 07 전력용수 ===============================
S7 = "07_전력용수"; ws = sh(S7, "07. 전력비 · 순수 · 폐수 산출 근거 (#9)", {"N": 10})
sec(ws, 3, "1) Batch 횟수 (연간)")
yhdr(ws, 4, "구분", "", ("Batch(kg)", "", "비고"))
yrow(ws, 5, "촉매 공정 Batch", "회/년", lambda y, c, p: f"='{S2}'!{c}{R2['kg']}/{R['b_proc']}", W1, k=f"={R['b_proc']}")
yrow(ws, 6, "전구체 Batch", "회/년", lambda y, c, p: f"='{S2}'!{c}{R2['kg']}/{R['b_prec']}", W1, k=f"={R['b_prec']}")
yrow(ws, 7, "분석 Batch", "회/년", lambda y, c, p: f"='{S2}'!{c}{R2['kg']}/{R['b_anal']}", W1, k=f"={R['b_anal']}", m="원본 #9: 2027은 전 설비 330회, 2028~ 전구체 264회·분석 366.7회로 혼재")
sec(ws, 9, "2) 전력비 산출근거 (일관 기준) = kW × Tact(h) × 전기요금 × 물가 × Batch 횟수")
yhdr(ws, 10, "공정", "설비", ("kW", "Tact(h)", "비고"))
cell(ws, "N10", "Batch구분", fill=HDR_FILL, font=HDR_FONT)
eq = [("촉매 합성", "합성 반응기", 5, 36, 5), ("열처리", "열처리로", 125, 55, 5), ("산처리/여과/세척", "산처리 여과 세척기", 1.5, 7, 5),
      ("건조/분쇄", "건조/분쇄기", 10, 14, 5), ("전구체 제조", "전구체 반응기", 2.5, 72, 6), ("전구체 제조", "전구체 제조 및 건조", 10, 96, 6),
      ("분석", "Fuel Cell Station", 3.3, 12, 7), ("분석", "XRD", 3, 0.5, 7), ("분석", "Chemisorption", 1.1, 8, 7), ("분석", "TGA", 1.5, 24, 7), ("분석", "BET", 2.2, 8, 7)]
for i, (a, b, kw, h, br) in enumerate(eq):
    r = 11 + i
    yrow(ws, r, a, b, lambda y, c, p, r=r, br=br: f"=$K{r}*$L{r}*{R['elec']}*(1+{R['infl']})^({c}$10-{R['base']})*{c}${br}", W,
         k=kw, l=h, m="열처리로가 전력비의 약 80%" if b == "열처리로" else ("BET는 #7 투자계획에 없음" if b == "BET" else None), kfmt=W1, lfmt=W1)
    cell(ws, f"N{r}", {5: "공정", 6: "전구체", 7: "분석"}[br])
yrow(ws, 22, "전력비 합계 (산출근거)", "원", lambda y, c, p: f"=SUM({c}11:{c}21)", W, tot=True)
yrow(ws, 24, "전력비 — 원본 손익 반영값", "원 (원본 #10)", [556239915, 682070618, 716174149, 751982856, 789581999, 829061099, 870514154], W, inp=True,
     m="원본 사업성분석·손익계획에 쓰인 값. 2028년 산출 근거 불명 (산출근거 대비 과다) → 21_보정손익")
yrow(ws, 25, "전력비 — 원본 #9 합계 (참고)", "원", [556239915, 569085969, 597540268, 627417281, 658788145, 691727553, 726313930], W, inp=True, m="원본 #9 산출근거 시트의 합계")
yrow(ws, 26, "차이 (원본 손익 − 산출근거)", "원", lambda y, c, p: f"={c}24-{c}22", W)
sec(ws, 28, "3) 순수 · 일반폐수 = 단가 × 배수(50배 × 세척횟수) × 물량(kg) × 물가")
yhdr(ws, 29, "구분", "", ("단가", "배수", "비고"))
yrow(ws, 30, "순수 (Cathode)", "원", lambda y, c, p: f"=$K30*$L30*'{S2}'!{c}{R2['kg']}*(1+{R['infl']})^({c}$29-{R['base']})", W, k=f"={R['water']}", l=f"={R['wmul']}*{R['wash']}", m="원본 비고의 '×세척횟수' 중복표기·'물량/1,000'은 실제 계산과 다름", kfmt=W1)
yrow(ws, 31, "일반폐수 (Cathode)", "원", lambda y, c, p: f"=$K31*$L31*'{S2}'!{c}{R2['kg']}*(1+{R['infl']})^({c}$29-{R['base']})", W, k=f"={R['waste']}", l=f"={R['wmul']}*{R['wash']}", kfmt=W1)
yrow(ws, 32, "Utility 합계 (손익 반영)", "원", lambda y, c, p: f"={c}24+{c}30+{c}31", W, tot=True, m="전력(원본 손익값) + 순수 + 폐수")
ws.freeze_panes = "D5"
R7 = dict(calc=22, orig=24, water=30, waste=31, util=32)

# =============================== 08 인원인건비 ===============================
S8 = "08_인원인건비"; ws = sh(S8, "08. 인원 및 인건비 (#8)", {"N": 10})
sec(ws, 3, "1) 직급별 연간 단가 (2024년 기준, 원)")
for col, v in zip("BCKL", ["직급", "직군", "노무비", "복리후생비"]):
    cell(ws, f"{col}4", v, fill=HDR_FILL, font=HDR_FONT)
grades = [("사원", "사무직", 47938500), ("대리", "사무직", 59416500), ("과장", "사무직", 72147000), ("차장", "사무직", 85562000),
          ("부장", "사무직", 99814000), ("선임부장", "사무직", 105095500), ("직계장", "사무직", 66379000),
          ("기능사원", "제조직", 53036891), ("기사", "제조직", 66070065), ("주임", "제조직", 70119988), ("기정", "제조직", 71986364), ("기성", "제조직", 84851935)]
for i, (g, t, v) in enumerate(grades):
    r = 5 + i
    cell(ws, f"B{r}", g); cell(ws, f"C{r}", t); cell(ws, f"K{r}", v, W, inp=True); cell(ws, f"L{r}", 8135390, W, inp=True)
GR = "$B$5:$B$16"; GK = "$K$5:$K$16"; GL = "$L$5:$L$16"
cell(ws, "M5", "※ 원본은 2024년 단가에 1.06을 1회만 곱함(기준연도 2026). 3년 적용시 → 21_보정손익")
sec(ws, 18, "2) 직무별 인원·인건비 — K: 비용구분, L: 항목, N: 직군 (집계용)")
yhdr(ws, 19, "직무", "항목", ("비용구분", "항목", "비고"))
cell(ws, "N19", "직군", fill=HDR_FILL, font=HDR_FONT)
roles = [("제조직", "제조원가", "기능직", 1.0, ["주임"] * 7), ("품질", "제조원가", "기능직", 0.5, ["주임"] * 7),
         ("자재", "제조원가", "기능직", 0.5, ["주임"] * 7), ("생산관리", "제조원가", "사무직", 1.0, ["사원", "대리", "대리", "대리", "대리", "과장", "과장"]),
         ("생산기술", "제조원가", "사무직", 0.5, ["과장"] * 7), ("영업", "판매비", "사무직", 0.5, ["과장"] * 7),
         ("인사", "관리비", "사무직", 0.5, ["과장"] * 7), ("전산", "관리비", "사무직", 0.5, ["과장"] * 7), ("재무", "관리비", "사무직", 0.5, ["과장"] * 7)]
r = 20
for name, cat, grp, fte, gr in roles:
    rf, rg, rn, rb, rt = r, r + 1, r + 2, r + 3, r + 4
    yrow(ws, rf, name, "인원(명)", fte, W1, inp=True, k=cat, l="인원"); cell(ws, f"N{rf}", grp)
    yrow(ws, rg, "", "직급", gr, None, inp=True, k=cat, l="직급", m="생산관리: 사원→대리('28)→과장('32)" if name == "생산관리" else None)
    yrow(ws, rn, "", "노무비(원)", lambda y, c, p, rf=rf, rg=rg: f"={c}{rf}*INDEX({GK},MATCH({c}{rg},{GR},0))*(1+{R['wage']})^({c}$19-{R['base']})", W, k=cat, l="노무")
    yrow(ws, rb, "", "복리후생비(원)", lambda y, c, p, rf=rf, rg=rg: f"={c}{rf}*INDEX({GL},MATCH({c}{rg},{GR},0))*(1+{R['wage']})^({c}$19-{R['base']})", W, k=cat, l="복리")
    yrow(ws, rt, "", "인건비(원)", lambda y, c, p, rn=rn, rb=rb: f"={c}{rn}+{c}{rb}", W, k=cat, l="인건비", tot=True)
    for rr in (rg, rn, rb, rt): cell(ws, f"N{rr}", grp)
    r += 5
end = r - 1; KR = f"$K$20:$K${end}"; LR = f"$L$20:$L${end}"; NR = f"$N$20:$N${end}"
def sumifs(c, cat, item, grp=None):
    rng = f"{c}$20:{c}${end}"
    return f"=SUMIFS({rng},{KR},\"{cat}\",{LR},\"{item}\")" if grp is None else f"=SUMIFS({rng},{LR},\"{item}\",{NR},\"{grp}\")"
r += 1; sec(ws, r, "3) 집계"); r += 1; yhdr(ws, r, "구분", "항목"); hr = r; r += 1
R8 = {}
for cat in ["제조원가", "판매비", "관리비"]:
    for item, lab in [("인원", "인원(명)"), ("노무", "노무비(원)"), ("복리", "복리후생비(원)"), ("인건비", "인건비(원)")]:
        yrow(ws, r, cat if item == "인원" else "", lab, lambda y, c, p, cat=cat, item=item: sumifs(c, cat, item), W1 if item == "인원" else W, tot=(item == "인건비"))
        R8[(cat, item)] = r; r += 1
r += 1
yrow(ws, r, "인원 합계", "사무직(명)", lambda y, c, p: sumifs(c, None, "인원", "사무직"), W1); R8["off"] = r; r += 1
yrow(ws, r, "", "기능직(명)", lambda y, c, p: sumifs(c, None, "인원", "기능직"), W1); R8["tech"] = r; r += 1
yrow(ws, r, "", "총계(명)", lambda y, c, p: f"={c}{r-2}+{c}{r-1}", W1, tot=True, m="※ 원본 '제조원가 소계 인원' 2032~33년 2.5명은 생산관리 과장 누락 오류 (정답 3.5명)"); R8["ppl"] = r; r += 1
yrow(ws, r, "인건비 총계", "노무비(원)", lambda y, c, p: f"={c}{R8[('제조원가','노무')]}+{c}{R8[('판매비','노무')]}+{c}{R8[('관리비','노무')]}", W); R8["lab"] = r; r += 1
yrow(ws, r, "", "복리후생비(원)", lambda y, c, p: f"={c}{R8[('제조원가','복리')]}+{c}{R8[('판매비','복리')]}+{c}{R8[('관리비','복리')]}", W); r += 1
yrow(ws, r, "", "인건비 총계(원)", lambda y, c, p: f"={c}{r-2}+{c}{r-1}", W, tot=True); R8["all"] = r; r += 2
sec(ws, r, "4) 기타 인원 관련 비용"); r += 1
yrow(ws, r, "지급수수료 (용역)", "인원(명)", lambda y, c, p: f"={R['out_n']}", W1); R8["out_n"] = r; r += 1
yrow(ws, r, "", "용역비(원)", lambda y, c, p: f"={c}{r-1}*{R['out_c']}*(1+{R['wage']})^({c}${hr}-{R['base']})", W, m="원본 손익 미반영 → 21_보정손익"); R8["out"] = r; r += 1
yrow(ws, r, "교육훈련비", "사무직(원)", lambda y, c, p: f"={R['edu_o']}*{c}{R8['off']}*(1+{R['wage']})^({c}${hr}-{R['base']})", W); r += 1
yrow(ws, r, "", "기능직(원)", lambda y, c, p: f"={R['edu_t']}*{c}{R8['tech']}*(1+{R['wage']})^({c}${hr}-{R['base']})", W); r += 1
yrow(ws, r, "", "합계(원)", lambda y, c, p: f"={c}{r-2}+{c}{r-1}", W, tot=True); R8["edu"] = r; r += 1
yrow(ws, r, "전산유지비", "사무직(원)", lambda y, c, p: f"={R['it']}*{c}{R8['off']}*(1+{R['wage']})^({c}${hr}-{R['base']})", W, tot=True); R8["it"] = r; r += 1
ws.freeze_panes = "D20"

# =============================== 09 투자감가 ===============================
S9 = "09_투자감가"; ws = sh(S9, "09. 투자계획 · 감가상각 (#7)", {"N": 10, "O": 30})
sec(ws, 3, "1) 설비 투자 계획 (원) — K: 단가, L: 대수, N: 물가적용연수, O: 사양")
yhdr(ws, 4, "공정", "설비명", ("단가(원)", "대수", "비고"))
cell(ws, "N4", "물가연수", fill=HDR_FILL, font=HDR_FONT); cell(ws, "O4", "사양", fill=HDR_FILL, font=HDR_FONT)
eqp = [("촉매 합성", "합성 반응기", 30650000, 3, 2, "50ℓ (유리)", "c"), ("열처리", "열처리로", 140000000, 5, 2, "열처리로 (웅비기계)", "c"),
       ("산처리/여과/세척", "산처리 여과 세척기", 88000000, 2, 2, "50ℓ 여과세척기 (프로콘eng.)", "c"), ("건조/분쇄", "건조/분쇄기", 268388455, 1, 2, "50ℓ SUS 건조 분쇄기 (프로콘eng.)", "c"),
       ("분석", "Fuel Cell Station", 123900000, 0, 2, "600W, 0~120A (싸이텍) · 필요 8대", "a"), ("분석", "XRD", 173000000, 0, 2, "X-PERT (Rigaku) · 필요 1대", "a"),
       ("분석", "Chemisorption", 120000000, 0, 2, "Autochem II 2920 (프로텍) · 필요 1대", "a"), ("분석", "TGA", 65000000, 0, 2, "TGA8000 (Perkin Elmer) · 필요 1대", "a"),
       ("전구체 제조", "염화백금산 반응기", 30650000, 1, 1, "50ℓ 유리 반응기 (이중자켓)", "p"), ("전구체 제조", "전구체 제조 및 건조", 49850000, 1, 1, "100ℓ 유리 반응기 + 155ℓ 열풍건조기", "p"),
       ("전구체 제조", "염화백금산 농축기", 0, 0, 1, "20ℓ 유리 농축기 (보유장비)", "p")]
R9 = {}
for i, (a, b, pr, q, n, spec, g) in enumerate(eqp):
    r = 5 + i
    yrow(ws, r, a, b, lambda y, c, p, r=r: f"=IF({c}$4={R['inv_y']},$K{r}*$L{r}*(1+{R['infl']})^$N{r},0)", W, k=pr, l=q,
         m=("분석설비: 도입 0대 (기존 장비 활용 가정)" if g == "a" else ("물가 1년만 적용 (촉매 설비는 2년) → 검토사항" if b == "염화백금산 반응기" else None)), kfmt=W)
    ws[f"L{r}"].fill = INP_FILL; ws[f"L{r}"].font = INP_FONT
    cell(ws, f"N{r}", n, "0", inp=True); cell(ws, f"O{r}", spec); R9[b] = r
yrow(ws, 16, "촉매 공정설비 소계", "", lambda y, c, p: f"=SUM({c}5:{c}8)", W, tot=True)
yrow(ws, 17, "분석설비 소계", "", lambda y, c, p: f"=SUM({c}9:{c}12)", W, tot=True)
yrow(ws, 18, "전구체 설비 소계", "", lambda y, c, p: f"=SUM({c}13:{c}15)", W, tot=True)
yrow(ws, 19, "설비 투자 합계", "원", lambda y, c, p: f"={c}16+{c}17+{c}18", W, tot=True)
cell(ws, "K19", f"=SUM({FIRST}19:{LAST}19)", W); cell(ws, "L19", "← 누적 투자")
sec(ws, 21, "2) 투자 요약 (억원)")
yhdr(ws, 22, "투자 유형", "", ("", "", "비고"))
yrow(ws, 23, "토지", "", 0, W1, inp=True, m="200평 기준 (공시지가 4,728,900원/평) — 기존 부지 활용 가정")
yrow(ws, 24, "건물", "", 0, W1, inp=True, m="200평 기준 (4,827,900원/평, 20년 상각) — 기존 남동공장 건물 활용 가정")
yrow(ws, 25, "기계장치", "", lambda y, c, p: f"={c}19/100000000", W1)
yrow(ws, 26, "전산 등", "", 0, W1, inp=True); yrow(ws, 27, "Utility", "", 0, W1, inp=True)
yrow(ws, 28, "Total", "억원", lambda y, c, p: f"=SUM({c}23:{c}27)", W1, tot=True)
sec(ws, 30, "3) 감가상각 · 수선비 · 설비금리 · 잔존가액 (원)")
yhdr(ws, 31)
yrow(ws, 32, "누적 투자액", "원", lambda y, c, p: f"=SUM(${FIRST}19:{c}19)", W)
yrow(ws, 33, "감가상각비 (정액)", "원", lambda y, c, p: f"=SUMPRODUCT(${FIRST}19:${LAST}19,(${FIRST}$31:${LAST}$31<={c}$31)*(${FIRST}$31:${LAST}$31>{c}$31-{R['dep_n']}))/{R['dep_n']}", W, tot=True, m="투자연도부터 상각연수 동안 정액")
yrow(ws, 34, "누적 감가상각", "원", lambda y, c, p: f"=SUM(${FIRST}33:{c}33)", W)
yrow(ws, 35, "설비 잔존가액", "원", lambda y, c, p: f"=MAX(0,{c}32-{c}34)", W, m="※ 원본 #10 잔존가액 수식 오류(2029년부터 음수) 수정")
yrow(ws, 36, "수선비", "원", lambda y, c, p: f"={c}32*{R['rep']}", W, m="설비가액 × 2% (원본과 동일: 상각 종료 후에도 계속)")
yrow(ws, 37, "설비금리 (참고)", "원", lambda y, c, p: f"={c}32*{R['eq_rate']}", W, m="원본 영업외비용 합계에 미포함 → 21_보정손익")
ws.freeze_panes = "D5"
R9.update(total=19, dep=33, rep=36, eqi=37, resid=35, cum=32, eok=28)

# =============================== 10 기존자산감가 ===============================
S10 = "10_기존자산감가"; ws = sh(S10, "10. 기존 자산 감가상각 원장 요약 (#16) — 부서: (케미칼)연료전지촉매 제조", {"B": 12, "C": 36, "D": 13, "E": 12})
heads = ["자산번호", "자산설명", "월 상각액", "상각 종료", "2025", "2026", "2027", "2028", "2025~ 합계"]
for i, h in enumerate(heads): cell(ws, f"{L(2+i)}4", h, fill=HDR_FILL, font=HDR_FONT)
assets = [("AE1002293", "이동식퓸크린홀(KF-200CA)", 41667, "2027-10", [500004, 500004, 416650, 0], 1416658),
          ("AM1002974", "1차 분산기(연료전지 백금 촉매)", 5763767, "2027-02", [69165204, 69165204, 10203580, 0], 148533988),
          ("AM1002975", "2차 고압분산기(연료전지 백금 촉매)", 5223370, "2027-02", [62680440, 62680440, 8042532, 0], 133403412),
          ("AM1002976", "합성 반응기(연료전지 백금촉매)", 6144330, "2027-02", [73731960, 73731960, 9487656, 0], 156951576),
          ("AM1002977", "여과/세척기 #1(연료전지 백금촉매)", 2637733, "2027-02", [31652796, 31652796, 3437713, 0], 66743305),
          ("AM1002978", "여과/세척기 #2(연료전지 백금촉매)", 2637733, "2027-02", [31652796, 31652796, 3437713, 0], 66743305),
          ("AM1002979", "건조/분쇄/열처리기 #1(연료전지 백금 촉매)", 3408034, "2027-05", [40896408, 40896408, 15647293, 0], 97440109),
          ("AM1002980", "건조/분쇄/열처리기 #2(연료전지 백금 촉매)", 3408034, "2027-05", [40896408, 40896408, 15647293, 0], 97440109),
          ("AM1003000", "글로브 박스(PT/C)", 641667, "2027-05", [7700004, 7700004, 3208315, 0], 18608323),
          ("AM1003094", "건조기 슬라이딩 도어", 441667, "2028-10", [5300004, 5300004, 5300004, 4416650], 20316662),
          ("AM1003095", "건조기 슬라이딩 도어_정부보조", -412706, "2028-10", [-4952472, -4952472, -4952472, -4127035], -18984451)]
for i, (a, b, m_, e, ys, t) in enumerate(assets):
    r = 5 + i
    for j, v in enumerate([a, b, m_, e] + ys):
        cell(ws, f"{L(2+j)}{r}", v, W if j >= 2 and j != 3 else None)
    cell(ws, f"J{r}", f"=SUM(F{r}:I{r})", W)
cell(ws, "B16", "총합계", fill=TOT_FILL, font=Font(bold=True)); cell(ws, "C16", "", fill=TOT_FILL)
for col in "DFGHIJ": cell(ws, f"{col}16", f"=SUM({col}5:{col}15)", W, fill=TOT_FILL)
ws["M18"] = "※ 월 상각액 합계 29,935,296원 × 60개월 ≈ 18.0억 → #15 자금수지 비고 \"'21년 투자비용(18.2억)\"과 대응 추정"
ws["M19"] = "※ 2027년 잔여 감가 0.70억은 원본 손익 미반영 → 21_보정손익 (선택)"
ws["M20"] = "※ 기존 합성반응기·여과세척기·건조/열처리기 보유 → 09 신규투자와 중복 여부 확인 필요"
ws["M21"] = "※ 연도별 금액은 원장 월별 값 합산(입력값). 2025~2026 = 월 상각액×12"
ws.column_dimensions["M"].width = 90
R10 = dict(y2027="H16", y2028="I16")

# =============================== 11 연구개발비 ===============================
S11 = "11_연구개발비"; ws = sh(S11, "11. 연구개발비 산출 근거 (#6, '21~'27, 원)")
rhy = list(range(2021, 2028))
for i, v in enumerate(["구분", "제조/개발"] + rhy + ["", "", "비고"]):
    cell(ws, f"{L(2+i)}4", v, fill=HDR_FILL, font=HDR_FONT)
rd = [("인건비", "제조", [0, 0, 0, 51714643, 54817522, 58106573, 61592967]), ("인건비", "개발", [434285922, 551390902, 612082510, 685810619, 726959256, 770576812, 816811420]),
      ("복리후생", "제조", [0, 0, 0, 7269757, 7705942, 8168299, 8658397]), ("복리후생", "개발", [53648205, 65990201, 104126219, 167121708, 177149010, 187777951, 199044628]),
      ("감가상각", "개발", [102281637, 485588747, 599202868, 492914267, 492914267, 492914267, 492914267]),
      ("소모품비", "개발", [91164780, 62998929, 38276330, 2762205, 2927937, 3103614, 3289830]),
      ("기타", "개발", [485867842, 164476212, 221101423, 168132501, 178220451, 188913678, 200248499])]
for i, (a, b, vals) in enumerate(rd):
    r = 5 + i; cell(ws, f"B{r}", a); cell(ws, f"C{r}", b)
    for j, v in enumerate(vals): cell(ws, f"{L(4+j)}{r}", v, W, inp=True)
cell(ws, "M9", "개발 감가 '24~'27 연 4.93억 ↔ 10_기존자산감가 원장 연 3.59억 (불일치)")
cell(ws, "M11", "지급수수료, 기술개발비, 여비교통비, 수선비, 접대비, 도서인쇄비, 무형자산 특허")
cell(ws, "B12", "비용 소계", fill=TOT_FILL); cell(ws, "C12", "제조+개발", fill=TOT_FILL)
cell(ws, "B13", "설비투자", ); cell(ws, "C13", "개발")
cell(ws, "B14", "합계", fill=TOT_FILL); cell(ws, "C14", "", fill=TOT_FILL)
for j, v in enumerate([869600000, 196060690, 973840000, 858703900, 0, 0, 0]):
    c = L(4 + j)
    cell(ws, f"{c}12", f"=SUM({c}5:{c}11)", W, fill=TOT_FILL); cell(ws, f"{c}13", v, W, inp=True); cell(ws, f"{c}14", f"={c}12+{c}13", W, fill=TOT_FILL)
cell(ws, "M12", "원본 비고 \"'25~'27: '24년 소계 적용\"과 달리 감가 외 항목은 연 6% 증가")
cell(ws, "B16", "총 연구개발 비용 ('21~'27)", font=Font(bold=True)); cell(ws, "J16", "=SUM(D14:J14)", W, fill=TOT_FILL)
cell(ws, "B17", "7년 균등 회수시 연간"); cell(ws, "J17", "=J16/7", W)
cell(ws, "M16", "원본 손익(관리비)에는 미반영 — 관리비 '연료전지촉매 개발팀 비용' 행 공란 → 21_보정손익 (선택)")
R11 = dict(total="$J$16")

# =============================== 12 Capa촉매 ===============================
S12 = "12_Capa촉매"; ws = sh(S12, "12. 연료전지 촉매 Capa (#18)")
procs = [("합성/숙성 반응기", "합성 반응기", 24, 4, 36, 0.65, 0.98), ("열처리로", "열처리로", 24, 4, 55, 0.65, 0.999),
         ("산처리/여과/세척기", "산처리 여과 세척기", 12, 5, 7, 0.32, 0.999), ("건조기/분쇄기", "건조/분쇄기", 24, 5, 14, 0.65, 0.999)]
cell(ws, "B4", "공정 No.", fill=HDR_FILL, font=HDR_FONT); cell(ws, "C4", "단위", fill=HDR_FILL, font=HDR_FONT)
for i, p in enumerate(procs): cell(ws, f"{L(4+i)}4", f"{i+1}. {p[0]}", fill=HDR_FILL, font=HDR_FONT)
rows12 = [("일수", "[日/月]"), ("장비가동시간", "[h/日]"), ("설비 대수", "[대]"), ("단위 중량", "[kg]"), ("가중 Tact", "[h]"), ("이론 Capa", "[kg/月]"),
          ("조업률", ""), ("부하율", ""), ("시간가동률", ""), ("성능가동률", ""), ("양품률", ""), ("설비종합효율", ""), ("설비 Capa", "[kg/月]"),
          ("생산가동률", ""), ("생산 Capa", "[kg/月]"), ("연간 Capa", "[kg/年]"), ("1대당 연간 Capa", "[kg/年·대]")]
for j, (a, u) in enumerate(rows12): cell(ws, f"B{5+j}", a); cell(ws, f"C{5+j}", u)
for i, (nm, eqn, hrs, wt, tact, op, yl) in enumerate(procs):
    c = L(4 + i)
    cell(ws, f"{c}5", 30, W, inp=True); cell(ws, f"{c}6", hrs, W, inp=True); cell(ws, f"{c}7", f"='{S9}'!$L${R9[eqn]}", W)
    cell(ws, f"{c}8", wt, W1 if wt else W, inp=True); cell(ws, f"{c}9", tact, W1, inp=True)
    cell(ws, f"{c}10", f"={c}5*{c}6*{c}7*{c}8/{c}9", W1)
    cell(ws, f"{c}11", op, P, inp=True); cell(ws, f"{c}12", 0.94, P, inp=True); cell(ws, f"{c}13", 0.85 if i != 2 else 0.83, P, inp=True)
    cell(ws, f"{c}14", 1.0, P, inp=True); cell(ws, f"{c}15", yl, P, inp=True)
    cell(ws, f"{c}16", f"={c}13*{c}14*{c}15", P); cell(ws, f"{c}17", f"={c}10*{c}11*{c}16", W1)
    cell(ws, f"{c}18", f"={c}12*{c}16", P); cell(ws, f"{c}19", f"={c}17*{c}12", W1, fill=TOT_FILL)
    cell(ws, f"{c}20", f"={c}19*12", W, fill=TOT_FILL); cell(ws, f"{c}21", f"=IF({c}7=0,0,{c}20/{c}7)", W1)
cell(ws, "B23", "병목 연간 Capa (kg/年)", font=Font(bold=True)); cell(ws, "D23", "=MIN(D20:G20)", W, fill=TOT_FILL)
cell(ws, "B24", "계획 물량 대비 가동률"); cell(ws, "D24", f"=MAX('{S2}'!{FIRST}{R2['kg']}:{LAST}{R2['kg']})/D23", P)
cell(ws, "B25", "종합 양품률"); cell(ws, "D25", "=PRODUCT(D15:G15)", P)
cell(ws, "M7", "설비 대수는 09_투자감가 대수와 연결")
cell(ws, "M17", "설비 Capa = 이론 × 조업률 × 설비종합효율, 생산 Capa = 설비 Capa × 부하율 (표시 % 기준 재계산, 원본 대비 ±0.2%)")
cell(ws, "M11", "※ 여과세척기: 가동 12h/日 + 조업률 32% → 반나절 이중 반영 의심 (24h 기준이면 Capa 2배)")
cell(ws, "M25", "→ 1,320kg 판매에 필요한 생산량 = 물량 ÷ 종합양품률 (원본 재료비 미반영 → 21_보정손익)")
R12 = dict(yield_="'12_Capa촉매'!$D$25", per={p[1]: f"'{S12}'!${L(4+i)}$21" for i, p in enumerate(procs)})

# =============================== 13 Capa전구체 ===============================
S13 = "13_Capa전구체"; ws = sh(S13, "13. 전구체 Capa (#19)")
pp = [("전구체 제조 반응기", "염화백금산 반응기", 12, 6, 72, 0.98, 0.83, 0.998), ("전구체 제조 및 건조", "전구체 제조 및 건조", 24, 5, 96, 0.95, 0.85, 0.975)]
cell(ws, "B4", "공정 No.", fill=HDR_FILL, font=HDR_FONT); cell(ws, "C4", "단위", fill=HDR_FILL, font=HDR_FONT)
for i, p in enumerate(pp): cell(ws, f"{L(4+i)}4", f"{i+1}. {p[0]}", fill=HDR_FILL, font=HDR_FONT)
rows13 = [("일수", "[日/月]"), ("장비가동시간", "[h/日]"), ("최대조업시간", "[h/月]"), ("설비 대수", "[대]"), ("단위 중량", "[kg]"), ("가중 Tact", "[h]"),
          ("이론 Capa", "[kg/月]"), ("조업률", ""), ("부하율", ""), ("시간가동률", ""), ("성능가동률", ""), ("양품률", ""), ("설비종합효율", ""),
          ("설비 Capa", "[kg/月]"), ("생산가동률", ""), ("생산 Capa", "[kg/月]"), ("연간 Capa (전구체)", "[kg/年]"), ("촉매 환산계수", "배"),
          ("연간 Capa (촉매기준)", "[kg/年]"), ("1대당 연간 Capa (촉매기준)", "[kg/年·대]")]
for j, (a, u) in enumerate(rows13): cell(ws, f"B{5+j}", a); cell(ws, f"C{5+j}", u)
for i, (nm, eqn, hrs, wt, tact, op, tm, yl) in enumerate(pp):
    c = L(4 + i)
    cell(ws, f"{c}5", 22, W, inp=True); cell(ws, f"{c}6", hrs, W, inp=True); cell(ws, f"{c}7", f"={c}5*{c}6", W)
    cell(ws, f"{c}8", f"='{S9}'!$L${R9[eqn]}", W); cell(ws, f"{c}9", wt, W1, inp=True); cell(ws, f"{c}10", tact, W1, inp=True)
    cell(ws, f"{c}11", f"={c}7/{c}10*{c}9*{c}8", W1); cell(ws, f"{c}12", op, P, inp=True); cell(ws, f"{c}13", 0.94, P, inp=True)
    cell(ws, f"{c}14", tm, P, inp=True); cell(ws, f"{c}15", 1.0, P, inp=True); cell(ws, f"{c}16", yl, P, inp=True)
    cell(ws, f"{c}17", f"={c}14*{c}15*{c}16", P); cell(ws, f"{c}18", f"={c}11*{c}12*{c}17", W1); cell(ws, f"{c}19", f"={c}13*{c}17", P)
    cell(ws, f"{c}20", f"={c}18*{c}13", W1, fill=TOT_FILL); cell(ws, f"{c}21", f"={c}20*12", W1)
    cell(ws, f"{c}22", [2.5242, 2.5425][i], "0.0000", inp=True); cell(ws, f"{c}23", f"={c}21*{c}22", W1, fill=TOT_FILL); cell(ws, f"{c}24", f"=IF({c}8=0,0,{c}23/{c}8)", W1)
cell(ws, "B26", "분자량 — 전구체"); cell(ws, "D26", 299.14, W2, inp=True)
cell(ws, "B27", "분자량 — 백금"); cell(ws, "D27", 195.084, "0.000", inp=True)
cell(ws, "B28", "백금 함량"); cell(ws, "D28", 0.65, P, inp=True)
cell(ws, "M11", "이론 Capa = 최대조업시간 ÷ Tact × 단위중량 × 대수")
cell(ws, "M22", "※ 원본 환산계수(≈2.55) 근거 불명 — 원본 촉매기준 508.49/620.94kg에 맞춘 입력값. 수식 확인 필요")
cell(ws, "M9", "※ 원본 #17 제목은 5KG/Batch, 이 시트는 6kg (확인 필요)")
R13 = dict(per={p[1]: f"'{S13}'!${L(4+i)}$24" for i, p in enumerate(pp)})

# =============================== 14 CapaBalance ===============================
S14 = "14_CapaBalance"; ws = sh(S14, "14. Capa Balance — 물량별 필요 설비 대수 (#17)", {"C": 14})
sec(ws, 3, "1) 계획 물량 기준 필요 대수 vs 투자 대수")
hd = ["설비", "구분", "1대 Capa(kg/年)", "계획물량(kg)", "필요 대수", "투자 대수", "부족 대수", "추가투자(원)", "", "", "비고"]
for i, h in enumerate(hd): cell(ws, f"{L(2+i)}4", h, fill=HDR_FILL, font=HDR_FONT)
bal = [("합성 반응기", "촉매", R12["per"]["합성 반응기"]), ("열처리로", "촉매", R12["per"]["열처리로"]), ("산처리 여과 세척기", "촉매", R12["per"]["산처리 여과 세척기"]),
       ("건조/분쇄기", "촉매", R12["per"]["건조/분쇄기"]), ("염화백금산 반응기", "전구체", R13["per"]["염화백금산 반응기"]), ("전구체 제조 및 건조", "전구체", R13["per"]["전구체 제조 및 건조"])]
for i, (nm, g, cap) in enumerate(bal):
    r = 5 + i
    cell(ws, f"B{r}", nm); cell(ws, f"C{r}", g); cell(ws, f"D{r}", f"={cap}", W1)
    cell(ws, f"E{r}", f"=MAX('{S2}'!{FIRST}{R2['kg']}:{LAST}{R2['kg']})", W); cell(ws, f"F{r}", f"=IF(D{r}=0,0,ROUNDUP(E{r}/D{r},0))", W)
    cell(ws, f"G{r}", f"='{S9}'!$L${R9[nm]}", W); cell(ws, f"H{r}", f"=MAX(0,F{r}-G{r})", W, font=WARN_FONT)
    cell(ws, f"I{r}", f"=H{r}*'{S9}'!$K${R9[nm]}*(1+{R['infl']})^'{S9}'!$N${R9[nm]}", W)
cell(ws, "B11", "추가투자 합계", fill=TOT_FILL); cell(ws, "I11", "=SUM(I5:I10)", W, fill=TOT_FILL)
cell(ws, "M5", "※ 전구체 설비는 Capa상 각 3대 필요하나 투자계획 1대 → 부족분은 21_보정손익 반영")
cell(ws, "M6", "※ 대안: 로터리킬른(1대 2,244kg/年) 1대로 열처리로 5대 대체 검토 (아래 대안 라인)")
sec(ws, 13, "2) 대안 라인 (원본 #17 입력값)")
alt = [("합성 반응기 50ℓ (대안)", 658), ("로터리킬른 (웅비기계)", 2244), ("여과세척기 (대안)", 4658), ("건조/분쇄기 (대안)", 19600), ("염화백금산 농축기", 2384.41)]
for i, (nm, cap) in enumerate(alt):
    r = 14 + i
    cell(ws, f"B{r}", nm); cell(ws, f"C{r}", "대안"); cell(ws, f"D{r}", cap, W1, inp=True)
    cell(ws, f"E{r}", f"=E5", W); cell(ws, f"F{r}", f"=ROUNDUP(E{r}/D{r},0)", W)
sec(ws, 20, "3) 물량별 필요 대수 표 (= ROUNDUP(물량 ÷ 1대 Capa))")
names = [b[0] for b in bal] + [a[0] for a in alt]
caps = [f"$D${5+i}" for i in range(6)] + [f"$D${14+i}" for i in range(5)]
cell(ws, "B21", "연간 물량(kg)", fill=HDR_FILL, font=HDR_FONT)
for i, nm in enumerate(names): cell(ws, f"{L(3+i)}21", nm, fill=HDR_FILL, font=HDR_FONT); ws[f"{L(3+i)}21"].alignment = Alignment(wrap_text=True)
for k in range(0, 253):
    r = 22 + k; v = k * 10
    cell(ws, f"B{r}", v, W)
    for i in range(11): ws[f"{L(3+i)}{r}"] = f"=IF($B{r}=0,0,ROUNDUP($B{r}/{caps[i]},0))"
ws.freeze_panes = "C22"
R14 = dict(add="'14_CapaBalance'!$I$11")

# =============================== 15 사업성분석 ===============================
S15 = "15_사업성분석"; ws = sh(S15, "15. 사업성분석 근거 — 원 단위 손익 (#10)")
yhdr(ws, 4, "구분", "항목", ("", "", "비고 / 연결"))
r15 = {}
def rr(key, r, b, c, f, fmt=W, tot=False, m=None, inp=False):
    yrow(ws, r, b, c, f, fmt, tot=tot, m=m, inp=inp); r15[key] = r
rr("sales", 5, "년 매출", "매출액 (원)", lambda y, c, p: f"='{S2}'!{c}{R2['sales']}", tot=True, m="02_물동시나리오")
rr("va", 6, "", "부가가치 (원)", lambda y, c, p: f"={c}5-{c}9", m="매출 − 재료비")
rr("var", 7, "", "부가가치율", lambda y, c, p: f"=IF({c}5=0,0,{c}6/{c}5)", P)
rr("cogs", 8, "매출원가", "합계 (원)", lambda y, c, p: f"=SUM({c}9:{c}21)", tot=True)
rr("mat", 9, "", "재료비", lambda y, c, p: f"='{S2}'!{c}{R2['mat']}", m="03_재료비")
rr("lab", 10, "", "노무비", lambda y, c, p: f"='{S8}'!{c}{R8[('제조원가','노무')]}", m="08: 제조직·품질·자재·생산관리·생산기술")
rr("wel", 11, "", "복리후생비", lambda y, c, p: f"='{S8}'!{c}{R8[('제조원가','복리')]}")
rr("elec", 12, "", "전력비 (변동비)", lambda y, c, p: f"='{S7}'!{c}{R7['orig']}", m="07: 원본 손익 반영값 (산출근거와 차이 → 21_보정손익)")
rr("water", 13, "", "순수비 (변동비)", lambda y, c, p: f"='{S7}'!{c}{R7['water']}")
rr("cons", 14, "", "소모품비 (변동비)", lambda y, c, p: f"='{S4}'!{c}{R4['total']}", m="04_소모품비")
rr("fee", 15, "", "지급수수료 (사외분석)", 0, inp=True)
rr("pack", 16, "", "포장비", lambda y, c, p: f"='{S5}'!{c}{R5['total']}", m="05_포장비")
rr("waste", 17, "", "일반폐수", lambda y, c, p: f"='{S7}'!{c}{R7['waste']}")
rr("rep", 18, "", "수선비 (고정비)", lambda y, c, p: f"='{S9}'!{c}{R9['rep']}", m="설비가액의 2%")
rr("ind", 19, "", "공장 간접비", 0, inp=True)
rr("rnd", 20, "", "경상개발비", 0, inp=True)
rr("dep", 21, "", "감가상각 (고정비)", lambda y, c, p: f"='{S9}'!{c}{R9['dep']}", m="09: 신규 설비 5년 정액")
rr("gp", 24, "매출총이익", "(원)", lambda y, c, p: f"={c}5-{c}8", tot=True)
rr("sell", 25, "판매비", "합계 (원)", lambda y, c, p: f"=SUM({c}26:{c}30)", tot=True)
rr("s_lab", 26, "", "노무비", lambda y, c, p: f"='{S8}'!{c}{R8[('판매비','노무')]}", m="08: 영업")
rr("s_wel", 27, "", "복리후생비", lambda y, c, p: f"='{S8}'!{c}{R8[('판매비','복리')]}")
rr("s_ent", 28, "", "영업 접대비", 0, inp=True)
rr("s_com", 29, "", "공통경비", lambda y, c, p: f"=({c}26+{c}27)*{R['comm']}", m="영업 인건비 × 50% (원본 역산)")
rr("s_oth", 30, "", "기타비용 (운반비)", lambda y, c, p: f"='{S6}'!{c}{R6['total']}", m="06_운반비")
rr("adm", 31, "관리비", "합계 (원)", lambda y, c, p: f"=SUM({c}32:{c}37)", tot=True, m="재경·인사·전산 노무비 및 경비")
rr("a_lab", 32, "", "노무비", lambda y, c, p: f"='{S8}'!{c}{R8[('관리비','노무')]}")
rr("a_wel", 33, "", "복리후생비", lambda y, c, p: f"='{S8}'!{c}{R8[('관리비','복리')]}")
rr("a_edu", 34, "", "교육훈련비", lambda y, c, p: f"='{S8}'!{c}{R8['edu']}")
rr("a_it", 35, "", "전산유지비", lambda y, c, p: f"='{S8}'!{c}{R8['it']}")
rr("a_env", 36, "", "환경인허가", 0, inp=True)
rr("a_dev", 37, "", "연료전지촉매 개발팀 비용", 0, inp=True, m="원본 공란 (R&D 136.8억 미반영) → 21_보정손익 선택 항목")
rr("op", 39, "영업이익", "(원)", lambda y, c, p: f"={c}24-{c}25-{c}31", tot=True)
rr("opm", 40, "", "영업이익률", lambda y, c, p: f"=IF({c}5=0,0,{c}39/{c}5)", P)
rr("nonop", 41, "영업외비용", "합계 (원)", lambda y, c, p: f"={c}42", tot=True, m="원본: 지급이자만 합산")
rr("int", 42, "", "금융비용 (지급이자)", [159781927, 117350407, 0, 0, 0, 0, 0], inp=True, m="원본 입력값 (산출 근거 불명)")
rr("inv_int", 43, "", "[참고] 금융비용 (재고+매출금리, 90일)", [162903622, 162142672, 161521797, 161044439, 160714282, 160535264, 160511590], inp=True, m="원본 합계 미포함 → 21_보정손익")
rr("eq_int", 44, "", "[참고] 금융비용 (설비금리)", lambda y, c, p: f"='{S9}'!{c}{R9['eqi']}", m="원본 합계 미포함 → 21_보정손익")
rr("ord", 46, "경상이익", "(원)", lambda y, c, p: f"={c}39-{c}41", tot=True)
rr("ordm", 47, "", "경상이익률", lambda y, c, p: f"=IF({c}5=0,0,{c}46/{c}5)", P)
sec(ws, 49, "투자 (원) — 09_투자감가 연결")
rr("inv", 50, "설비", "투자비용", lambda y, c, p: f"='{S9}'!{c}{R9['total']}")
rr("invc", 51, "", "누적 투자비용", lambda y, c, p: f"='{S9}'!{c}{R9['cum']}")
rr("resid", 52, "", "잔존가액 (투자 − 누적감가)", lambda y, c, p: f"='{S9}'!{c}{R9['resid']}", m="원본 음수 오류 수정")
ws.freeze_panes = "D5"

# =============================== 16 손익계획 ===============================
S16 = "16_손익계획"; ws = sh(S16, "16. 수익성 — 손익계획 (#5)")
def X(key, c): return f"'{S15}'!{c}{r15[key]}"
sec(ws, 3, "1) 손익계획 (억원)")
yhdr(ws, 4, "구분", "", ("7년 합계", "", "비고"))
pl = [("kg", "LT 촉매량 (kg)", lambda c: f"='{S2}'!{c}{R2['kg']}", W),
      ("sales", "매출액", lambda c: f"={X('sales',c)}/1E8", W1), ("mat", "재료비 (원재료비: Pt·카본)", lambda c: f"={X('mat',c)}/1E8", W1),
      ("va", "부가가치액", lambda c: f"={c}6-{c}7", W1), ("mfg", "제조원가 (노무비+제조경비)", lambda c: f"={c}10+{c}13", W1),
      ("lab", "  노무비", lambda c: f"={c}11+{c}12", W1), ("lab1", "    급여 外", lambda c: f"={X('lab',c)}/1E8", W1), ("lab2", "    복리후생비", lambda c: f"={X('wel',c)}/1E8", W1),
      ("exp", "  제조경비", lambda c: f"=SUM({c}14:{c}18)", W1),
      ("util", "    Utility (전력·순수·폐수)", lambda c: f"=({X('elec',c)}+{X('water',c)}+{X('waste',c)})/1E8", W1),
      ("dep", "    감가상각비", lambda c: f"={X('dep',c)}/1E8", W1), ("cons", "    소모품비", lambda c: f"={X('cons',c)}/1E8", W1),
      ("rnd", "    경상개발비", lambda c: f"={X('rnd',c)}/1E8", W1),
      ("oth", "    기타경비 (포장·수선·간접·수수료)", lambda c: f"=({X('pack',c)}+{X('rep',c)}+{X('ind',c)}+{X('fee',c)})/1E8", W1),
      ("gp", "매출총이익", lambda c: f"={c}8-{c}9", W1), ("sell", "판매비", lambda c: f"={X('sell',c)}/1E8", W1),
      ("dci", "직접비 차감이익", lambda c: f"={c}19-{c}20", W1), ("adm", "관리비", lambda c: f"={X('adm',c)}/1E8", W1),
      ("op", "영업이익", lambda c: f"={c}21-{c}22", W1), ("fin", "금융비용", lambda c: f"={X('nonop',c)}/1E8", W1),
      ("ord", "경상이익", lambda c: f"={c}23-{c}24", W1), ("cum", "경상이익 누계", None, W1)]
r16 = {}
for i, (k, lab, f, fmt) in enumerate(pl):
    r = 5 + i; r16[k] = r
    if k == "cum":
        yrow(ws, r, lab, "", lambda y, c, p: f"=SUM(${FIRST}{r-1}:{c}{r-1})", fmt, tot=True)
    else:
        yrow(ws, r, lab, "", lambda y, c, p, f=f: f(c), fmt, tot=k in ("sales", "va", "gp", "op", "ord"))
        cell(ws, f"K{r}", f"=SUM({FIRST}{r}:{LAST}{r})", fmt)
cell(ws, "M25", "※ 비율은 모두 매출 대비로 통일 (원본은 판매비 이하를 부가가치 대비로 계산 → 1,048% 등 왜곡)")
sec(ws, 28, "2) 매출 대비 비율")
yhdr(ws, 29, "구분", "", ("7년", "", ""))
for i, k in enumerate(["mat", "va", "mfg", "gp", "sell", "adm", "op", "ord"]):
    r = 30 + i; lab = [x[1] for x in pl if x[0] == k][0]
    yrow(ws, r, lab.strip(), "% of 매출", lambda y, c, p, k=k: f"=IF({c}$6=0,0,{c}{r16[k]}/{c}$6)", P)
    cell(ws, f"K{r}", f"=IF(K$6=0,0,K{r16[k]}/K$6)", P)
sec(ws, 39, "3) 촉매 1g당 손익 (원/g)")
yhdr(ws, 40, "구분", "", ("", "", "비고"))
G = lambda c: f"'{S2}'!{c}{R2['sup_g']}"
ug = [("price", "판가", lambda c: f"={X('sales',c)}/{G(c)}"), ("mat", "(-) 재료비", lambda c: f"={X('mat',c)}/{G(c)}"),
      ("va", "부가가치", lambda c: f"={c}41-{c}42"), ("lab", "(-) 노무비", lambda c: f"=({X('lab',c)}+{X('wel',c)})/{G(c)}"),
      ("fix", "(-) 고정비 (Utility+감가+경상개발)", lambda c: f"=({X('elec',c)}+{X('water',c)}+{X('waste',c)}+{X('dep',c)}+{X('rnd',c)})/{G(c)}"),
      ("var", "(-) 변동비 (소모품+기타경비)", lambda c: f"=({X('cons',c)}+{X('pack',c)}+{X('rep',c)}+{X('ind',c)}+{X('fee',c)})/{G(c)}"),
      ("sga", "(-) 판관비 (판매+관리)", lambda c: f"=({X('sell',c)}+{X('adm',c)})/{G(c)}"),
      ("cost", "제조원가 (총원가)", lambda c: f"={c}42+{c}44+{c}45+{c}46+{c}47"), ("proc", "가공비 (제조원가 − 재료비)", lambda c: f"={c}48-{c}42"),
      ("op", "영업이익", lambda c: f"={c}41-{c}48"), ("fin", "금융비용", lambda c: f"={X('nonop',c)}/{G(c)}")]
r16g = {}
for i, (k, lab, f) in enumerate(ug):
    r = 41 + i; r16g[k] = r
    yrow(ws, r, lab, "원/g", lambda y, c, p, f=f: f(c), W1, tot=k in ("price", "cost", "op"))
cell(ws, "M45", "원본 분류 유지: Utility(전력)를 고정비, 수선비를 변동비로 분류 (일반 분류와 반대 → 검토사항)")
cell(ws, "M49", "#1 시트 'Cathode 1 가공비'와 동일 (2027: 1,171원/g)")
ws.freeze_panes = "D5"

# =============================== 17 투자회수 ===============================
S17 = "17_투자회수"; ws = sh(S17, "17. 투자회수 (#14, 억원)")
yhdr(ws, 4, "구분", "", ("7년 합계", "", "비고"))
def P16(k, c): return f"'{S16}'!{c}{r16[k]}"
yrow(ws, 5, "현금유입", "경상이익", lambda y, c, p: f"={P16('ord',c)}", W1)
yrow(ws, 6, "", "감가상각비", lambda y, c, p: f"={P16('dep',c)}", W1)
yrow(ws, 7, "", "계", lambda y, c, p: f"={c}5+{c}6", W1, tot=True)
yrow(ws, 8, "현금유출", "법인세 등", lambda y, c, p: f"=MAX(0,{c}5)*{R['tax']}", W1, m="경상이익 × 24.2% (이월결손금 미고려)")
yrow(ws, 9, "", "투자", lambda y, c, p: f"='{S9}'!{c}{R9['eok']}", W1)
yrow(ws, 10, "", "계", lambda y, c, p: f"={c}8+{c}9", W1, tot=True)
yrow(ws, 11, "순현금", "당해", lambda y, c, p: f"={c}7-{c}10", W1, tot=True)
yrow(ws, 12, "", "누적", lambda y, c, p: f"=SUM(${FIRST}11:{c}11)", W1, tot=True)
yrow(ws, 13, "", "누적≥0 여부", lambda y, c, p: f"=IF({c}12>=0,1,0)", "0")
for r in range(5, 12):
    cell(ws, f"K{r}", f"=SUM({FIRST}{r}:{LAST}{r})", W1)
cell(ws, "B15", "예상 회수기간", font=Font(bold=True))
cell(ws, "D15", f"=IF(COUNTIF({FIRST}13:{LAST}13,0)=7,\"회수 불가 (2033년 누적 \"&TEXT({LAST}12,\"#,##0.0\")&\"억)\",IF(COUNTIF({FIRST}13:{LAST}13,0)=0,\"1년 이내\",COUNTIF({FIRST}13:{LAST}13,0)-INDEX({FIRST}12:{LAST}12,COUNTIF({FIRST}13:{LAST}13,0))/INDEX({FIRST}11:{LAST}11,COUNTIF({FIRST}13:{LAST}13,0)+1)))", W1, fill=TOT_FILL, font=WARN_FONT)
ws.merge_cells("D15:G15")
cell(ws, "M15", "누적 순현금이 0 이상이 되는 시점(년, 선형 보간). 원본은 공란")
cell(ws, "M16", "→ 투자가 복수일 경우: ① 투자 건별 회수기간 산출 또는 ② 건별 회수기간을 투자금액으로 가중평균")

# =============================== 18 자금수지 ===============================
S18 = "18_자금수지"; ws = sh(S18, "18. 자금수지 (#15, 억원) — 수식 오류 수정본")
yhdr(ws, 4, "구분", "", ("7년 합계", "", "비고"))
SA = lambda c: f"'{S15}'!{c}"
yrow(ws, 5, "전년 이월", "", lambda y, c, p: "=0" if y == 2027 else f"={p}22", W1)
yrow(ws, 6, "CASH-IN", "매출 수금", lambda y, c, p: (f"={SA(c)}{r15['sales']}/1E8*(12-{R['col_m']})/12" if y == 2027 else f"=({SA(c)}{r15['sales']}*(12-{R['col_m']})/12+{SA(p)}{r15['sales']}*{R['col_m']}/12)/1E8"), W1, m="당해 매출 11/12 + 전년 매출 1/12 (원본은 2027년 수금 0 → 오류)")
yrow(ws, 7, "", "소계", lambda y, c, p: f"={c}6", W1, tot=True)
yrow(ws, 8, "CASH-OUT", "자재 대금", lambda y, c, p: (f"={SA(c)}{r15['mat']}/1E8*(1+{R['inv_m']}/12)" if y == 2027 else f"=({SA(c)}{r15['mat']}+({SA(c)}{r15['mat']}-{SA(p)}{r15['mat']})*{R['inv_m']}/12)/1E8"), W1, m="매입 당일결제 + 재고(1개월분) 증감 (원본 2027년 7.1억은 1개월 재고분만 반영 → 오류)")
yrow(ws, 9, "", "인건비 (제조)", lambda y, c, p: f"=({SA(c)}{r15['lab']}+{SA(c)}{r15['wel']})/1E8", W1)
yrow(ws, 10, "", "제경비 (감가 제외)", lambda y, c, p: f"='{S16}'!{c}{r16['exp']}-'{S16}'!{c}{r16['dep']}", W1)
yrow(ws, 11, "", "판매비·관리비", lambda y, c, p: f"=({SA(c)}{r15['sell']}+{SA(c)}{r15['adm']})/1E8", W1, m="원본 누락 → 추가")
yrow(ws, 12, "", "금융비용", lambda y, c, p: f"='{S16}'!{c}{r16['fin']}", W1, m="※ 2029년 이후 차입금 이자 미반영 (원본 동일)")
yrow(ws, 13, "", "법인세 등", lambda y, c, p: f"='{S17}'!{c}8", W1)
yrow(ws, 14, "", "투자", lambda y, c, p: f"='{S17}'!{c}9", W1)
yrow(ws, 15, "", "소계", lambda y, c, p: f"=SUM({c}8:{c}14)", W1, tot=True)
yrow(ws, 17, "자금수지", "당해 년도", lambda y, c, p: f"={c}7-{c}15", W1, tot=True)
yrow(ws, 18, "", "차기 이월", lambda y, c, p: f"={c}5+{c}17", W1)
yrow(ws, 20, "차입금", "당해 년도", lambda y, c, p: f"=MAX(0,-{c}17)", W1)
yrow(ws, 21, "", "누계 (= −차기이월)", lambda y, c, p: f"=MAX(0,-{c}18)", W1, tot=True)
yrow(ws, 22, "", "(이월 연결용)", lambda y, c, p: f"={c}18", W1)
for r in [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17]: cell(ws, f"K{r}", f"=SUM({FIRST}{r}:{LAST}{r})", W1)
sec(ws, 24, "[참고] 원본 #15 값 (억원)")
yhdr(ws, 25, "구분", "", ("7년 합계", "", ""))
orig15 = [("매출 수금", [0, 101.3, 99.3, 97.3, 95.3, 93.4, 91.6]), ("자재 대금", [7.1, 93.1, 97.8, 102.7, 107.8, 113.2, 114.7]),
          ("인건비", [2.7, 3.0, 3.1, 3.3, 3.5, 3.9, 4.2]), ("제경비", [7.8, 9.1, 9.6, 10.0, 10.5, 11.0, 11.6]),
          ("CASH-OUT 소계", [33.8, 106.4, 110.5, 116.0, 121.8, 128.1, 130.5]), ("당해 자금수지", [-33.8, -5.1, -11.2, -18.7, -26.5, -34.7, -38.9]),
          ("차입금 누계", [33.8, 38.8, 50.0, 68.7, 95.2, 129.9, 168.8])]
for i, (lab, v) in enumerate(orig15):
    r = 26 + i; yrow(ws, r, lab, "원본", v, W1, inp=True); cell(ws, f"K{r}", f"=SUM({FIRST}{r}:{LAST}{r})", W1)
yrow(ws, 34, "차입금 누계 차이", "수정 − 원본", lambda y, c, p: f"={c}21-{c}32", W1, tot=True)
ws.freeze_panes = "D5"

# =============================== 19 보고자료 ===============================
S19 = "19_보고자료"; ws = sh(S19, "19. Case 1 : 두산퓨얼셀 Cathode (4 kg/batch) 보고자료 (#2)")
sec(ws, 3, "1. 매출 · 손익 (억원)")
yhdr(ws, 4, "구분", "", ("7년 합계", "", "관련 시트"))
rep = [("총 촉매 소요량 (kg/년)", f"'{S2}'!{{c}}{R2['kg']}", W, "02_물동시나리오"), ("기준판가 (원/g)", f"'{S2}'!{{c}}{R2['price']}", W, "단가인하율 2%"),
       ("매출액", f"'{S16}'!{{c}}{r16['sales']}", W1, ""), ("재료비", f"'{S16}'!{{c}}{r16['mat']}", W1, "물가상승률 5%"),
       ("부가가치액", f"'{S16}'!{{c}}{r16['va']}", W1, ""), ("제조원가", f"'{S16}'!{{c}}{r16['mfg']}", W1, ""),
       ("   노무비", f"'{S16}'!{{c}}{r16['lab']}", W1, ""), ("   제조경비", f"'{S16}'!{{c}}{r16['exp']}", W1, ""),
       ("판매비", f"'{S16}'!{{c}}{r16['sell']}", W1, ""), ("직접비 차감이익", f"'{S16}'!{{c}}{r16['dci']}", W1, ""),
       ("관리비", f"'{S16}'!{{c}}{r16['adm']}", W1, "R&D('21~'27) 미반영"), ("영업이익", f"'{S16}'!{{c}}{r16['op']}", W1, ""),
       ("금융비용", f"'{S16}'!{{c}}{r16['fin']}", W1, ""), ("경상이익", f"'{S16}'!{{c}}{r16['ord']}", W1, ""),
       ("영업이익률 (매출 대비)", None, P, "")]
for i, (lab, f, fmt, note) in enumerate(rep):
    r = 5 + i
    if f is None: yrow(ws, r, lab, "", lambda y, c, p: f"=IF({c}7=0,0,{c}16/{c}7)", fmt)
    else:
        yrow(ws, r, lab, "", lambda y, c, p, f=f: "=" + f.format(c=c), fmt, m=note, tot=lab in ("매출액", "영업이익", "경상이익"))
        if i >= 2: cell(ws, f"K{r}", f"=SUM({FIRST}{r}:{LAST}{r})", fmt)
sec(ws, 21, "2. 투자 (억원)")
yhdr(ws, 22, "구분", "", ("", "", ""))
yrow(ws, 23, "투자금액", "기계장치", lambda y, c, p: f"='{S9}'!{c}25", W1, m="합성반응기, 여과/세척기, 건조/분쇄/열처리기, 전구체 설비")
sec(ws, 25, "3. 인원 및 인건비")
yhdr(ws, 26, "구분", "", ("", "", ""))
yrow(ws, 27, "인원 (명)", "사무직", lambda y, c, p: f"='{S8}'!{c}{R8['off']}", W1)
yrow(ws, 28, "", "기능직", lambda y, c, p: f"='{S8}'!{c}{R8['tech']}", W1)
yrow(ws, 29, "", "계", lambda y, c, p: f"='{S8}'!{c}{R8['ppl']}", W1, tot=True)
yrow(ws, 30, "인건비 합계 (억원)", "", lambda y, c, p: f"='{S8}'!{c}{R8['all']}/1E8", W1, m="임금 상승률 6%")
sec(ws, 32, "4. 제조경비 (억원)")
yhdr(ws, 33, "구분", "", ("", "", "비고"))
ce = [("전력비", "elec", "전기요금 190원/kWh"), ("순수", "water", "7.7원/kg"), ("일반폐수", "waste", "150원/kg"), ("감가상각비", "dep", "설비 5년"),
      ("소모품비", "cons", ""), ("포장비", "pack", ""), ("수선비", "rep", "설비가액의 2%")]
for i, (lab, k, note) in enumerate(ce):
    yrow(ws, 34 + i, lab, "", lambda y, c, p, k=k: f"={X(k,c)}/1E8", W2, m=note)
yrow(ws, 41, "계", "", lambda y, c, p: f"=SUM({c}34:{c}40)", W2, tot=True)
sec(ws, 43, "5. 금융비용 (억원)")
yrow(ws, 44, "지급이자", "", lambda y, c, p: f"={X('int',c)}/1E8", W2)

# =============================== 20 입찰시뮬 ===============================
S20 = "20_입찰시뮬"; ws = sh(S20, "20. 두산퓨얼셀 연료전지 촉매 입찰 시뮬레이션 (4 kg/batch) (#1)")
sec(ws, 3, "1) 기본 조건")
cell(ws, "B4", "적용"); cell(ws, "C4", "사양"); cell(ws, "D4", "판가 (원/g)"); cell(ws, "E4", "2027 물동량 (g)")
for c_ in "BCDE": ws[f"{c_}4"].fill = HDR_FILL; ws[f"{c_}4"].font = HDR_FONT
cell(ws, "B5", "Cathode (발전용)"); cell(ws, "C5", "16.7% PtCrCo/C")
cell(ws, "D5", f"='{S2}'!{FIRST}{R2['price']}", W, fill=PatternFill("solid", fgColor="FFFF00")); cell(ws, "E5", f"='{S2}'!{FIRST}{R2['sup_g']}", W, fill=PatternFill("solid", fgColor="FFFF00"))
cell(ws, "M5", "※ 원본 #1은 판가 칸에 7,657(제조원가)을 표기했으나 매출은 7,818(판가) 기준")
sec(ws, 7, "2) 2027년 원가 구조 (원/g 촉매)")
heads = ["구분", "재료비", "노무비", "고정비", "변동비", "판관비", "제조원가", "가공비(원가)", "제시 가공비", "판가(LT메탈)"]
for i, h in enumerate(heads): cell(ws, f"{L(2+i)}8", h, fill=HDR_FILL, font=HDR_FONT)
cell(ws, "B9", "Cathode")
for i, k in enumerate(["mat", "lab", "fix", "var", "sga", "cost", "proc"]):
    cell(ws, f"{L(3+i)}9", f"='{S16}'!{FIRST}{r16g[k]}", W)
cell(ws, "J9", f"={R['proc']}", W); cell(ws, "K9", "=C9+J9", W, fill=PatternFill("solid", fgColor="C6EFCE"))
cell(ws, "M9", "제시 가공비 = $0.9 × 1,480원 / 판가 = 재료비 + 제시 가공비 / 가공비(원가) = 제조원가 − 재료비")
cell(ws, "B10", "제시 가공비 − 원가 가공비 (원/g)"); cell(ws, "J10", "=J9-I9", W, fill=TOT_FILL)
sec(ws, 12, "3) LT소재 공급가 비교 (#1 메모)")
lt = [("LT소재 공급단가 (원/g)", f"={R['lt_amt']}/({R['lt_kg']}*1000)", W1, "12억 ÷ 110kg"),
      ("(-) 재료비 (원/g, 2027)", "=C9", W1, ""), ("LT소재 가공비 (원/g)", "=D13-D14", W1, "공급단가 − 재료비"),
      ("LT소재 가공비 ($/g)", f"=D15/{R['fx']}", W2, ""), ("목표 가공비 ($/g)", f"=TEXT({R['tgt_lo']},\"0.0\")&\" ~ \"&TEXT({R['tgt_hi']},\"0.0\")", None, "#1 요청사항 (Anode $0.6/g)"),
      ("목표 대비 배수", f"=D16/{R['tgt_hi']}", W2, "LT소재 가공비 ÷ 목표 상한")]
for i, (lab, f, fmt, note) in enumerate(lt):
    r = 13 + i; cell(ws, f"B{r}", lab); cell(ws, f"D{r}", f, fmt, fill=TOT_FILL if i in (2, 3) else None); cell(ws, f"M{r}", note)
sec(ws, 20, "4) 년도별 예상 손익 (억원)")
yhdr(ws, 21, "구분", "", ("7년 소계", "", "비고"))
sim = [("물량 (kg)", "kg", W), ("매출", "sales", W1), ("부가가치", "va", W1), ("영업이익", "op", W1), ("경상이익", "ord", W1)]
for i, (lab, k, fmt) in enumerate(sim):
    r = 22 + i; yrow(ws, r, lab, "", lambda y, c, p, k=k: f"='{S16}'!{c}{r16[k]}", fmt, tot=k in ("op",))
    cell(ws, f"K{r}", f"=SUM({FIRST}{r}:{LAST}{r})", fmt)
yrow(ws, 27, "부가가치율 (매출 대비)", "", lambda y, c, p: f"=IF({c}23=0,0,{c}24/{c}23)", P); cell(ws, "K27", "=IF(K23=0,0,K24/K23)", P)
yrow(ws, 28, "영업이익률 (매출 대비)", "", lambda y, c, p: f"=IF({c}23=0,0,{c}25/{c}23)", P); cell(ws, "K28", "=IF(K23=0,0,K25/K23)", P)
sec(ws, 30, "5) 가공비 민감도 · 손익분기 가공비 (판가 = 재료비 + 가공비, 이후 연 2% 인하)")
cell(ws, "B31", "판가 1원/g 변화의 7년 매출 효과 (원)"); cell(ws, "D31", f"=SUMPRODUCT('{S2}'!{FIRST}{R2['sup_g']}:{LAST}{R2['sup_g']},'{S2}'!{FIRST}{R2['disc']}:{LAST}{R2['disc']})", W)
cell(ws, "B32", "원본 기준 7년 영업이익 (원)"); cell(ws, "D32", f"=SUM('{S15}'!{FIRST}{r15['op']}:{LAST}{r15['op']})", W)
cell(ws, "B33", "보정 기준 7년 경상이익 (원)"); cell(ws, "D33", "='21_보정손익'!K40", W)
cell(ws, "B34", "원본 7년 경상이익 (원)"); cell(ws, "D34", f"=SUM('{S15}'!{FIRST}{r15['ord']}:{LAST}{r15['ord']})", W)
for i, h in enumerate(["가공비 ($/g)", "가공비 (원/g)", "2027 판가", "7년 영업이익(억)", "7년 경상이익(억, 원본)", "7년 경상이익(억, 보정)"]):
    cell(ws, f"{L(2+i)}36", h, fill=HDR_FILL, font=HDR_FONT)
cases = [0.8, 0.9, 1.0, 1.2, 1.5, 2.0, 2.5, "=D16"]
for i, v in enumerate(cases):
    r = 37 + i
    cell(ws, f"B{r}", v, W2, inp=not isinstance(v, str)); cell(ws, f"C{r}", f"=B{r}*{R['fx']}", W)
    cell(ws, f"D{r}", f"=$C$9+C{r}", W)
    cell(ws, f"E{r}", f"=($D$32+(C{r}-{R['proc']})*$D$31)/1E8", W1)
    cell(ws, f"F{r}", f"=($D$34+(C{r}-{R['proc']})*$D$31)/1E8", W1)
    cell(ws, f"G{r}", f"=($D$33+(C{r}-{R['proc']})*$D$31)/1E8", W1)
cell(ws, "M44", "← LT소재 현 가공비 수준")
cell(ws, "B46", "손익분기 가공비 ($/g)", font=Font(bold=True))
for i, (lab, src) in enumerate([("7년 영업이익 = 0", "$D$32"), ("7년 경상이익 = 0 (원본)", "$D$34"), ("7년 경상이익 = 0 (보정)", "$D$33")]):
    r = 47 + i; cell(ws, f"B{r}", lab); cell(ws, f"D{r}", f"=({R['proc']}-{src}/$D$31)/{R['fx']}", W2, fill=TOT_FILL, font=WARN_FONT)
    cell(ws, f"E{r}", f"=D{r}*{R['fx']}", W); cell(ws, f"F{r}", "원/g")
cell(ws, "M47", "가공비 변화는 매출에만 영향 (원가·판관비 불변) → 선형 계산이 정확함")

# =============================== 21 보정손익 ===============================
S21 = "21_보정손익"; ws = sh(S21, "21. 보정 손익 — 원본 누락·오류 반영 (K열 1=반영, 0=미반영)")
yhdr(ws, 4, "구분", "보정 항목", ("반영(1/0)", "", "근거"))
cell(ws, "N4", "7년 합계(원)", fill=HDR_FILL, font=HDR_FONT); ws.column_dimensions["N"].width = 16
yrow(ws, 5, "원본 경상이익", "15_사업성분석", lambda y, c, p: f"='{S15}'!{c}{r15['ord']}", W, tot=True)
adj = [("1. 전력비", "산출근거(일관 Batch) 적용", lambda y, c, p: f"='{S7}'!{c}{R7['orig']}-'{S7}'!{c}{R7['calc']}", 1, "원본 손익 전력비(2028~ 근거 불명) → 07 산출근거로 대체 (+는 이익 개선)"),
       ("2. 용역비", "지급수수료 3명 반영", lambda y, c, p: f"=-'{S8}'!{c}{R8['out']}", 1, "#8에 산출되었으나 손익 미반영"),
       ("3. 금융비용", "재고+매출금리 (90일)", lambda y, c, p: f"=-'{S15}'!{c}{r15['inv_int']}", 1, "#10에 산출되었으나 영업외비용 합계 미포함"),
       ("4. 금융비용", "설비금리 5%", lambda y, c, p: f"=-'{S9}'!{c}{R9['eqi']}", 1, "#10에 산출되었으나 영업외비용 합계 미포함"),
       ("5. 양품률", "재료비 ÷ 종합양품률", lambda y, c, p: f"=-'{S15}'!{c}{r15['mat']}*(1/{R12['yield_']}-1)", 1, "#18 종합양품률 97.7% → 판매량 대비 추가 생산 재료비 (#4 '제조로스 2%' 미적용)"),
       ("6. 전구체 설비", "Capa 부족분 추가투자 감가·수선", lambda y, c, p: f"=-({R14['add']}/{R['dep_n']})*(AND({c}$4>={R['inv_y']},{c}$4<{R['inv_y']}+{R['dep_n']}))-{R14['add']}*{R['rep']}*({c}$4>={R['inv_y']})", 1, "#17·#19: 전구체 설비 각 3대 필요 vs 투자 1대"),
       ("7. 기존자산", "잔여 감가상각", lambda y, c, p: (f"=-'{S10}'!{R10['y2027']}" if y == 2027 else (f"=-'{S10}'!{R10['y2028']}" if y == 2028 else "=0")), 1, "#16 원장: 2027년 0.70억 (#6 비고 '27년 감가 반영'과 달리 미반영)"),
       ("8. 임금상승", "'24 기준단가에 3년 상승 적용", lambda y, c, p: f"=-'{S8}'!{c}{R8['all']}*((1+{R['wage']})^(2027-2024)/(1+{R['wage']})^(2027-{R['base']})-1)", 0, "원본은 1년(1.06)만 적용. 선택"),
       ("9. 산처리 질산", "9% 질산 단가 적용", lambda y, c, p: f"=-'{S4}'!{c}{R4['acid']}*('{S4}'!$F$13/'{S4}'!$F$7-1)*'{S2}'!{c}{R2['sup_g']}", 0, "단가표엔 9% 질산(5.80원/g)인데 계산은 65%(1.80원/g). 확인 후 선택"),
       ("10. 연구개발비", "'21~'27 개발비 7년 균등 회수", lambda y, c, p: f"=-'{S11}'!{R11['total']}/7", 0, "#6 총 136.8억. 관리비 비고는 '반영'이나 실제 0. 매몰비용 처리 여부 경영판단")]
for i, (a, b, f, flag, note) in enumerate(adj):
    r = 7 + i
    yrow(ws, r, a, b, f, W, m=note); cell(ws, f"K{r}", flag, "0", inp=True); cell(ws, f"N{r}", f"=SUM({FIRST}{r}:{LAST}{r})", W)
yrow(ws, 18, "보정 합계 (반영분)", "", lambda y, c, p: f"=SUMPRODUCT($K$7:$K$16,{c}7:{c}16)", W, tot=True); cell(ws, "N18", f"=SUM({FIRST}18:{LAST}18)", W)
yrow(ws, 19, "보정 경상이익", "(원)", lambda y, c, p: f"={c}5+{c}18", W, tot=True); cell(ws, "N19", f"=SUM({FIRST}19:{LAST}19)", W)
yrow(ws, 20, "보정 경상이익 누계", "(원)", lambda y, c, p: f"=SUM(${FIRST}19:{c}19)", W)
cell(ws, "N5", f"=SUM({FIRST}5:{LAST}5)", W)
sec(ws, 22, "요약 (억원)")
yhdr(ws, 23, "구분", "", ("7년 합계", "", ""))
yrow(ws, 24, "원본 경상이익", "", lambda y, c, p: f"={c}5/1E8", W1); cell(ws, "K24", f"=SUM({FIRST}24:{LAST}24)", W1)
yrow(ws, 25, "보정 경상이익", "", lambda y, c, p: f"={c}19/1E8", W1, tot=True); cell(ws, "K25", f"=SUM({FIRST}25:{LAST}25)", W1)
yrow(ws, 26, "차이", "", lambda y, c, p: f"={c}25-{c}24", W1); cell(ws, "K26", f"=K25-K24", W1)
yrow(ws, 27, "참고: R&D 포함시 경상이익", "", lambda y, c, p: f"=({c}19+IF($K$16=1,0,{c}16))/1E8", W1); cell(ws, "K27", f"=SUM({FIRST}27:{LAST}27)", W1)
cell(ws, "B30", "※ 2029년 이후 누적 차입금 이자(18_자금수지)는 순환참조 방지를 위해 미반영 — 반영시 추가 악화", font=WARN_FONT)
cell(ws, "J40", "7년 보정 경상이익(원) →"); cell(ws, "K40", "=N19", W)
ws.freeze_panes = "D5"

# =============================== 22 검토사항 ===============================
S22 = "22_검토사항"; ws = sh(S22, "22. 검토사항 — 원본 오류·불일치·누락 목록", {"B": 6, "C": 14, "D": 14, "E": 28, "F": 60, "G": 46, "H": 14})
heads = ["No", "유형", "원본 시트", "항목", "내용", "모델 처리", "영향"]
for i, h in enumerate(heads): cell(ws, f"{L(2+i)}3", h, fill=HDR_FILL, font=HDR_FONT)
issues = [
 ("누락", "#6·#10", "연구개발비 136.8억", "관리비 비고 \"'21~'27 개발비용 반영\"이나 관리비 = 관리 인건비+교육+전산만 (원 단위 일치). '개발팀 비용' 행 공란", "21_보정손익 #10 (선택, 기본 미반영)", "='21_보정손익'!N16/1E8"),
 ("누락", "#10", "금융비용 (재고·매출금리, 설비금리)", "산출되었으나 영업외비용 합계에는 지급이자만 포함", "21_보정손익 #3·#4", "=('21_보정손익'!N9+'21_보정손익'!N10)/1E8"),
 ("누락", "#8·#10", "용역비 (지급수수료 3명)", "#8에 연 1.34억 산출, 손익 어디에도 없음 (사외분석 수수료 0)", "21_보정손익 #2", "='21_보정손익'!N8/1E8"),
 ("불일치", "#9↔#10", "전력비", "손익의 2028년 전력비 6.82억 vs 산출근거 5.69억 (근거 불명). 이후 매년 5% 차이 누적", "07에 두 값 병기, 21_보정손익 #1", "='21_보정손익'!N7/1E8"),
 ("불일치", "#9", "전력 Batch 횟수", "2027 전 설비 330회 / 2028~ 전구체 264회·분석 366.7회 혼재. 전구체 1대 264×72h=19,008h > 8,760h (물리적 불가)", "01_가정 Batch 기준 통일 (공정 4·전구체 5·분석 4kg)", "-"),
 ("누락", "#4·#18", "양품률·제조로스", "종합 양품률 97.7%, #4 비고 '제조로스 2% 반영'이나 재료비 = 원단위×판매량 (미적용)", "21_보정손익 #5", "='21_보정손익'!N11/1E8"),
 ("Capa 부족", "#7↔#17·#19", "전구체 설비", "Capa상 염화백금산 반응기·전구체 제조/건조 각 3대 필요, 투자 각 1대", "14_CapaBalance 부족대수·추가투자, 21_보정손익 #6", "='21_보정손익'!N12/1E8"),
 ("누락", "#16·#6", "기존자산 잔여 감가", "2027년 0.70억 (원장) — #6 비고 '사업성 Sheet 27년 감가 반영'과 달리 미반영", "21_보정손익 #7", "='21_보정손익'!N13/1E8"),
 ("수식오류", "#15", "2027년 매출 수금", "수금 0 (2028년 수식은 '전년 1/12 + 당해 11/12' → 2027년은 94.6억이어야 함)", "18_자금수지 수정", "-"),
 ("수식오류", "#15", "자재 대금", "2027년 7.1억(1개월 재고분만), 2028~32 재료비+3~4억, 2033 = 재료비로 연도별 로직 상이", "18_자금수지: 매입 당일결제 + 재고증감", "-"),
 ("누락", "#15", "판매비·관리비 현금유출", "자금수지 CASH-OUT에 없음 (7년 약 18억)", "18_자금수지 추가", "-"),
 ("누락", "#15", "차입금 이자", "2029년 이후 차입금 50→169억 증가에도 금융비용 0", "미반영 (순환참조) — 별도 검토", "-"),
 ("수식오류", "#10", "설비 잔존가액", "1,447.6→1,158.1→434.3→△48.3… (2029년 감가 2.5배 차감, 음수)", "09 잔존가액 = MAX(0, 투자 − 누적감가)", "-"),
 ("표시오류", "#5·#2·#1", "영업이익 % 등", "판매비 이하 % 를 부가가치 대비로 계산 (1,048%, △48% 등)", "16 매출 대비로 통일", "-"),
 ("표기오류", "#5", "원/g 표 연도", "2027~2031, 2033, 2034 (2032 누락)", "16 2027~2033", "-"),
 ("표기오류", "#4", "물동 재료비 연도", "헤더 2026~2032, 값은 2027~2033", "03 수정", "-"),
 ("표기오류", "#3", "단위", "매출액·부가가치 단위 '백만원' → 실제 '원'", "02 수정", "-"),
 ("수식오류", "#8", "제조원가 인원 소계", "2032~33년 2.5명 (생산관리 과장 누락, 금액은 포함)", "08 SUMIFS 집계로 수정 (3.5명)", "-"),
 ("불일치", "#4", "원재료 소요량", "Pt 0.120 = 0.118×1.02 (비고 0.12g+2%), Cr 0.014·Co 0.021 (비고 0.027g·0.02g+25%), 카본 0.867 (비고 0.86+0.2%)", "원본 셀값 사용 (Pt 0.12 기준이면 연 1.25억 증가)", "-"),
 ("불일치", "#4·#11", "제품 표기", "상단 라벨 14.6% PtCrCo/C, Cr 1.2% (#4) vs 16.7%, Cr 2.7%", "16.7% 기준", "-"),
 ("불일치", "#11", "산처리 질산 단가", "단가표 산처리 = 9% 질산 5.80원/g, 계산은 65% 1.80원/g. 9%가 65%보다 비싼 것도 확인 필요", "21_보정손익 #9 (선택)", "='21_보정손익'!N15/1E8"),
 ("표기오류", "#11", "각주", "KOH '수산화칼슘' → 수산화칼륨, 항목번호 1-1 → 1-4", "04 수정", "-"),
 ("불일치", "#12↔기타", "Batch 기준", "포장비 3,600g/Batch (타 시트 4,000g) — 수율 90% 가정 흔적?", "01_가정 입력값으로 분리", "-"),
 ("불일치", "#7", "물가 적용연수", "촉매 설비 1.05² vs 전구체 설비 1.05¹", "09 N열 입력 (원본 유지)", "-"),
 ("불일치", "#2↔#10", "수선비율", "#2 비고 5% vs 실제 2% (#10 비고 2%)", "2% 사용", "-"),
 ("불일치", "#10↔#7·#14", "투자연도", "#10 투자 2026년 vs #7·#14 2027년", "2027 (01_가정)", "-"),
 ("불일치", "#15↔#7", "투자 비고", "\"'21년 투자비용(18.2억) '27년 투자 반영\" vs 실제 14.5억 — 18.2억은 기존자산(#16, 약 18.0억)으로 추정", "-", "-"),
 ("확인필요", "#16↔#7", "기존 설비 중복", "기존 합성반응기·여과세척기 2·건조/열처리기 2 보유(2027 상각완료) vs 신규 동일 설비 투자", "-", "-"),
 ("확인필요", "#18", "여과세척기 Capa", "가동 12h/日 + 조업률 32% (타 65%) → 이중 반영 의심, 맞으면 1대로 충분", "12 입력값 원본 유지", "-"),
 ("확인필요", "#19", "촉매 환산계수", "전구체→촉매 ≈2.55배 근거 불명, Batch 6kg vs #17 5kg 표기", "13 입력값", "-"),
 ("확인필요", "#8", "임금 기준연도", "2024 단가에 1.06 1회만 적용 (3년이면 +12%)", "21_보정손익 #8 (선택)", "='21_보정손익'!N14/1E8"),
 ("분류", "#1·#5", "원가 분류", "전력(Utility)을 고정비, 수선비를 변동비로 분류 (일반 분류와 반대)", "원본 분류 유지, 표기만", "-"),
 ("확인필요", "#14", "회수기간", "원본 공란 → 누적 순현금 지속 감소로 회수 불가", "17 자동 산출", "='17_투자회수'!D15"),
 ("정정", "-", "2032년 손익 개선", "감가상각(설비 5년) 2031년 종료 효과 — 수식 오류 아님", "-", "-")]
for i, it in enumerate(issues):
    r = 4 + i
    cell(ws, f"B{r}", i + 1)
    for j, v in enumerate(it):
        x = cell(ws, f"{L(3+j)}{r}", v, W1 if j == 5 and v.startswith("=") else None, wrap=True)
    ws[f"H{r}"].alignment = Alignment(horizontal="right", vertical="top")
cell(ws, f"B{6+len(issues)}", "영향(억원): 7년 합계, (−)는 손익 악화")
ws.freeze_panes = "B4"

N_ISSUES = len(issues)
# =============================== 23 원본검증 ===============================
S23 = "23_원본검증"; ws = sh(S23, "23. 원본 대비 검증 — 모델 계산값과 원본(붙여넣기) 값 비교")
yhdr(ws, 4, "항목", "구분", ("최대 차이", "판정", "비고"))
chk = [("매출액", "sales", [10319802707, 10113406653, 9911138520, 9712915750, 9518657435, 9328284286, 9141718600]),
       ("재료비", "mat", [8561562707, 8989640843, 9439122885, 9911079029, 10406632981, 10926964630, 11473312861]),
       ("부가가치", "va", [1758240000, 1123765810, 472015635, -198163279, -887975546, -1598680344, -2331594261]),
       ("매출원가", "cogs", [9895295469, 10487731054, 10999162732, 11536344109, 12100573357, 12421755027, 13045323557]),
       ("노무비", "lab", [237707095, 264866202, 280758174, 297603664, 315459884, 352445935, 373592691]),
       ("복리후생비", "wel", [30182296, 31993234, 33912828, 35947598, 38104454, 40390721, 42814164]),
       ("소모품비", "cons", [94613792, 99344482, 104311706, 109527291, 115003656, 120753839, 126791531]),
       ("포장비", "pack", [20020000, 21021000, 22072050, 23175653, 24334435, 25551157, 26828715]),
       ("순수", "water", [3735270, 3922034, 4118135, 4324042, 4540244, 4767256, 5005619]),
       ("일반폐수", "waste", [72765000, 76403250, 80223413, 84234583, 88446312, 92868628, 97512059]),
       ("수선비", "rep", [28951763] * 7), ("감가상각", "dep", [289517629] * 5 + [0, 0]),
       ("매출총이익", "gp", [424507239, -374324401, -1088024212, -1823428359, -2581915923, -3093470741, -3903604957]),
       ("판매비", "sell", [80456500, 85117570, 90049988, 95269620, 100793261, 106638693, 112824744]),
       ("관리비", "adm", [131922920, 139838295, 148228593, 157122308, 166549647, 176542626, 187135183]),
       ("영업이익", "op", [212127819, -599280266, -1326302793, -2075820287, -2849258830, -3376652060, -4203564883]),
       ("경상이익", "ord", [52345892, -716630673, -1326302793, -2075820287, -2849258830, -3376652060, -4203564883])]
r = 5
for lab, k, vals in chk:
    yrow(ws, r, lab, "원본", vals, W, inp=True)
    yrow(ws, r + 1, "", "모델", lambda y, c, p, k=k: f"='{S15}'!{c}{r15[k]}", W)
    yrow(ws, r + 2, "", "차이", lambda y, c, p, r=r: f"={c}{r+1}-{c}{r}", W)
    cell(ws, f"K{r}", f"=MAX(MAX({FIRST}{r+2}:{LAST}{r+2}),-MIN({FIRST}{r+2}:{LAST}{r+2}))", W)
    cell(ws, f"L{r}", f"=IF(K{r}<={R['tol']},\"일치\",\"차이\")", None, font=Font(bold=True))
    r += 3
extra = [("판가 원/g (#5)", f"'{S16}'!{{c}}{r16g['price']}", [7818, 7662, 7508, 7358, 7211, 7067, 6926], 1),
         ("제조원가 원/g (#5)", f"'{S16}'!{{c}}{r16g['cost']}", [7657.3, 8115.7, 8513.2, 8930.9, 9369.6, 9625.0, 10110.1], 0.1),
         ("가공비 원/g (#5)", f"'{S16}'!{{c}}{r16g['proc']}", [1171.3, 1305.3, 1362.4, 1422.5, 1485.8, 1346.9, 1418.2], 0.1),
         ("인건비 총계 (#8)", f"'{S8}'!{{c}}{R8['all']}", [438088058, 477270022, 505906224, 536260597, 568436233, 620600865, 657836916], 10),
         ("경상이익 억원 (#5)", f"'{S16}'!{{c}}{r16['ord']}", [0.5, -7.2, -13.3, -20.8, -28.5, -33.8, -42.0], 0.05),
         ("투자 순현금 누적 (#14)", f"'{S17}'!{{c}}12", [-11.2, -15.5, -25.8, -43.7, -69.3, -103.0, -145.1], 0.15)]
for lab, f, vals, tol in extra:
    yrow(ws, r, lab, "원본", vals, W1, inp=True)
    yrow(ws, r + 1, "", "모델", lambda y, c, p, f=f: "=" + f.format(c=c), W1)
    yrow(ws, r + 2, "", "차이", lambda y, c, p, r=r: f"={c}{r+1}-{c}{r}", W2)
    cell(ws, f"K{r}", f"=MAX(MAX({FIRST}{r+2}:{LAST}{r+2}),-MIN({FIRST}{r+2}:{LAST}{r+2}))", W2)
    cell(ws, f"L{r}", f"=IF(K{r}<={tol},\"일치\",\"차이\")", None, font=Font(bold=True))
    cell(ws, f"M{r}", f"허용오차 {tol} (원본 표시 반올림)")
    r += 3
cell(ws, f"B{r}", "투자 합계 (#7)"); cell(ws, f"D{r}", 1447588147, W, inp=True); cell(ws, f"E{r}", f"='{S9}'!K19", W); cell(ws, f"K{r}", f"=ABS(E{r}-D{r})", W); cell(ws, f"L{r}", f"=IF(K{r}<=1,\"일치\",\"차이\")"); r += 1
capo = [("Capa 합성 (#18)", "'12_Capa촉매'!D20", 1467), ("Capa 열처리 (#18)", "'12_Capa촉매'!E20", 1632), ("Capa 여과세척 (#18)", "'12_Capa촉매'!F20", 1537),
        ("Capa 건조분쇄 (#18)", "'12_Capa촉매'!G20", 1603), ("Capa 전구체반응기 촉매기준 (#19)", "'13_Capa전구체'!D23", 508.49), ("Capa 전구체건조 촉매기준 (#19)", "'13_Capa전구체'!E23", 620.94)]
for lab, f, v in capo:
    cell(ws, f"B{r}", lab); cell(ws, f"D{r}", v, W1, inp=True); cell(ws, f"E{r}", "=" + f, W1)
    cell(ws, f"K{r}", f"=ABS(E{r}/D{r}-1)", P); cell(ws, f"L{r}", f"=IF(K{r}<=0.01,\"일치\",\"차이\")"); cell(ws, f"M{r}", "표시 % 기준 재계산 → 허용 1%"); r += 1
r += 1
cell(ws, f"B{r}", "전체 판정", font=Font(bold=True, size=12)); cell(ws, f"D{r}", f"=IF(COUNTIF(L5:L{r-2},\"차이\")=0,\"전 항목 일치\",COUNTIF(L5:L{r-2},\"차이\")&\"개 항목 차이\")", None, fill=TOT_FILL, font=WARN_FONT)
R23_total = f"'{S23}'!D{r}"
ws.freeze_panes = "D5"

# =============================== 00 목차 ===============================
S0 = "00_목차"; ws = wb.create_sheet(S0, 0); ws.sheet_view.showGridLines = False
ws["B1"] = "두산퓨얼셀 연료전지 Cathode 촉매 사업성분석 — 통합 모델"; ws["B1"].font = Font(bold=True, size=16)
ws["B2"] = "원본 19개 시트를 수식으로 재연결. 입력값(파란 글씨·노란 셀)만 바꾸면 전 시트 자동 반영."
ws["B3"] = f"원본 재현 검증 결과:"; ws["D3"] = f"={R23_total}"; ws["D3"].font = WARN_FONT
for col, w in zip("BCDEF", [18, 26, 12, 60, 50]): ws.column_dimensions[col].width = w
heads = ["시트", "내용", "원본 시트", "주요 연결 (입력 ← / 출력 →)", "비고"]
for i, h in enumerate(heads): cell(ws, f"{L(2+i)}5", h, fill=HDR_FILL, font=HDR_FONT)
toc = [(S1, "기본 가정 (모든 입력값)", "-", "→ 전 시트", "물량·가공비·상승률·단가·Batch 기준"),
       (S2, "물동 시나리오 (제시물량·판가·시장규모·매출/부가가치)", "#3", "← 01, 03 / → 15", "판가 = 재료비 원단위 + 가공비, 연 2% 인하"),
       (S3, "재료비", "#4", "← 01, 02 / → 02, 15", "Pt·Cr·Co·카본 소요량 × 단가 × 물가"),
       (S4, "소모품비", "#11", "← 01, 02 / → 15", "수소(열처리)가 62%"),
       (S5, "포장비", "#12", "← 01, 02 / → 15", ""), (S6, "운반비", "#13", "← 01 / → 15 판매비", ""),
       (S7, "전력·순수·폐수", "#9", "← 01, 02 / → 15, 21", "원본 손익값과 산출근거 병기"),
       (S8, "인원·인건비", "#8", "← 01 / → 15 (노무·판매·관리), 21", "직급표 × 인원 × 임금상승"),
       (S9, "투자·감가·수선·잔존가액", "#7 (#8 중복본)", "← 01 / → 12·13 대수, 14, 15, 17", ""),
       (S10, "기존자산 감가 원장", "#16", "→ 21", ""), (S11, "연구개발비 '21~'27", "#6", "→ 21", "총 136.8억"),
       (S12, "촉매 Capa", "#18", "← 09 대수 / → 14, 21(양품률)", ""), (S13, "전구체 Capa", "#19", "← 09 대수 / → 14", ""),
       (S14, "Capa Balance", "#17", "← 02, 09, 12, 13 / → 21", "필요 vs 투자 대수, 부족분"),
       (S15, "사업성분석 (원 단위 손익)", "#10", "← 02~09 / → 16, 21, 23", "손익의 원본"),
       (S16, "손익계획 (억원·%·원/g)", "#5", "← 15 / → 17, 18, 19, 20", "% 매출 대비 통일"),
       (S17, "투자회수", "#14", "← 16, 09 / → 18", "회수기간 자동"),
       (S18, "자금수지", "#15", "← 15, 16, 17", "수식 오류 수정 + 원본 비교"),
       (S19, "보고자료 (Case 1)", "#2", "← 02, 08, 09, 15, 16", ""),
       (S20, "입찰 시뮬레이션", "#1", "← 16, 21 / 가공비 민감도", "손익분기 가공비"),
       (S21, "보정 손익", "신규", "← 07, 08, 09, 10, 11, 12, 14, 15", "누락·오류 반영 (K열 스위치)"),
       (S22, "검토사항", "신규", "", f"오류·불일치 {N_ISSUES}건"), (S23, "원본 검증", "신규", "← 15, 16, 8, 9, 12, 13, 17", "원본 값과 자동 대조")]
for i, row_ in enumerate(toc):
    r = 6 + i
    for j, v in enumerate(row_):
        c = cell(ws, f"{L(2+j)}{r}", v)
        if j == 0: c.hyperlink = f"#'{v}'!A1"; c.font = Font(color="0563C1", underline="single")
r = 6 + len(toc) + 1
notes = ["작성 원칙",
         "1. 원본 손익(15·16)은 붙여넣은 원본 값을 원 단위까지 재현 (23_원본검증에서 자동 확인).",
         "2. 계산 근거를 알 수 없는 원본 값(2028년~ 전력비, 지급이자, 재고·매출금리, 전구체 환산계수)은 입력값으로 두고 비고에 표시.",
         "3. 손익에 영향 없는 명백한 오류(자금수지, 잔존가액, % 기준, 연도·단위 표기, 인원 집계)는 직접 수정.",
         "4. 손익에 영향 있는 누락·불일치는 21_보정손익에서 항목별 스위치(1/0)로 반영 → 원본과 보정 결과 비교.",
         "5. 숨은 소수점 2개(카본 0.8672738g, MEA 0.1127145g)는 원본 합계에 맞춰 역산 (검토사항 참고)."]
for i, t in enumerate(notes):
    ws[f"B{r+i}"] = t
    if i == 0: ws[f"B{r+i}"].font = Font(bold=True)

wb._sheets.sort(key=lambda s: s.title)
wb.calculation.fullCalcOnLoad = True
wb.save(OUT); print("saved", OUT)
