import sys
import os
import numpy as np
import pandas as pd

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QFileDialog, QLineEdit,
    QTreeWidget, QTreeWidgetItem, QMessageBox, QProgressDialog,
    QCheckBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

import matplotlib
matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from matplotlib.lines import Line2D


# ============================================================
# КОЛОНКИ ЛОГА
# ============================================================
EXPECTED = ["t_recv", "rack", "gateway", "t_send",
            "varid", "value", "valid_flag"]

KEY_COL    = "varid"      # что анализируем (список/графики)
RACK_COL   = "rack"       # стойка-источник
VALUE_COL  = "value"
VALID_COL  = "valid_flag"


# ============================================================
# ОПИСАНИЯ ГРАФИКОВ
# ============================================================
CHART_DESCRIPTIONS = {
    "value_time": (
        "📈 <b>Значение сигнала во времени</b><br>"
        "<b>Оси:</b> X — время приёма, Y — значение сигнала.<br>"
        "<b>Что показывает:</b> как меняется сигнал и в какие моменты он был недостоверным.<br>"
        "<b>Как читать:</b> зелёные точки — достоверные (valid_flag=0), красные — "
        "недостоверные. Серая линия — тренд.<br>"
        "<b>На что смотреть:</b> скопления красных точек, резкие скачки, «залипание», "
        "разрывы во времени."
    ),
    "quality": (
        "🚦 <b>Качество сигнала</b><br>"
        "<b>Оси:</b> X — категории, Y — количество записей.<br>"
        "<b>Что показывает:</b> долю достоверных и недостоверных измерений.<br>"
        "<b>Как читать:</b> зелёный — valid_flag=0, красный — valid_flag≠0. "
        "Над столбцами — число и процент.<br>"
        "<b>На что смотреть:</b> если красный > 5–10% — сигнал проблемный."
    ),
    "heatmap": (
        "🔥 <b>Тепловая карта недостоверности по времени</b><br>"
        "<b>Оси:</b> X — время (бины по 1 мин), Y — одна строка.<br>"
        "<b>Что показывает:</b> в какие минуты доля недостоверных была высокой.<br>"
        "<b>Как читать:</b> белый — 0%, тёмно-красный — 100% недостоверных.<br>"
        "<b>На что смотреть:</b> вертикальные полосы — массовые сбои; "
        "равномерный фон — постоянная нестабильность."
    ),
    "latency": (
        "⏱ <b>Задержка доставки</b><br>"
        "<b>Оси:</b> X — время приёма, Y — t_recv − t_send (мс).<br>"
        "<b>Что показывает:</b> сколько сигнал шёл от стойки до шлюза.<br>"
        "<b>Как читать:</b> зелёные — достоверные, красные — нет. "
        "Пунктир — медиана.<br>"
        "<b>На что смотреть:</b> пики latency, совпадающие с красными точками; "
        "рост медианы во времени."
    ),
    "hist_value": (
        "📊 <b>Распределение значений</b><br>"
        "<b>Оси:</b> X — значение сигнала, Y — частота.<br>"
        "<b>Что показывает:</b> в каком диапазоне чаще всего находится сигнал.<br>"
        "<b>Как читать:</b> узкий пик — сигнал стабилен; широкий разброс — «гуляет»; "
        "несколько пиков — режимы работы.<br>"
        "<b>На что смотреть:</b> выбросы, значения 0 или максимум — часто признак сбоя."
    ),
    "delta_hist": (
        "Δ <b>Распределение изменений</b><br>"
        "<b>Оси:</b> X — ΔValue, Y — частота.<br>"
        "<b>Что показывает:</b> насколько сильно сигнал меняется от замера к замеру.<br>"
        "<b>Как читать:</b> пик около нуля — плавный сигнал; широкий разброс — резкие "
        "изменения; второй пик — скачки/дребезг.<br>"
        "<b>На что смотреть:</b> большие ΔValue — подозрительные скачки."
    ),
    "rate": (
        "📉 <b>Скорость изменения</b><br>"
        "<b>Оси:</b> X — время, Y — ΔValue / Δt.<br>"
        "<b>Что показывает:</b> как быстро меняется сигнал в каждый момент.<br>"
        "<b>Как читать:</b> ровная линия около нуля — сигнал спокоен; всплески — "
        "быстрые изменения.<br>"
        "<b>На что смотреть:</b> совпадение пиков с недостоверными замерами, "
        "периодические всплески."
    ),
}


MINT_STYLE = """
    QMainWindow, QWidget#Main { background-color: #F3F7F5; }
    QWidget#Card, QWidget#Sidebar { 
        background-color: #FFFFFF; border: 1px solid #E2ECE7; border-radius: 12px; 
    }
    QPushButton {
        background-color: transparent; color: #6B7C74; border: none; border-radius: 6px;
        padding: 10px 14px; font-size: 13px; text-align: left;
    }
    QPushButton:hover { background-color: #F0F6F3; }
    QPushButton:checked { background-color: #E6F4ED; color: #10B981; font-weight: bold; }
    QPushButton#ActionBtn {
        background-color: #10B981; color: #FFFFFF; font-weight: bold; text-align: center;
    }
    QPushButton#ActionBtn:hover { background-color: #059669; }
    QLineEdit {
        background-color: #FAFDFB; color: #1A3025; border: 1px solid #D1E2DB;
        border-radius: 6px; padding: 6px 10px; font-size: 12px;
    }
    QLineEdit:focus { border: 1px solid #10B981; background-color: #FFFFFF; }
    QTreeWidget {
        background-color: #FAFDFB; color: #1A3025; border: 1px solid #D1E2DB;
        border-radius: 6px; padding: 4px; font-size: 12px;
    }
    QTreeWidget::item { padding: 5px 6px; border-radius: 4px; }
    QTreeWidget::item:selected { background-color: #E6F4ED; color: #10B981; font-weight: bold; }
    QTreeWidget::item:hover { background-color: #F0F6F3; }
    QHeaderView::section {
        background-color: #F0F6F3; color: #1A3025; border: none;
        padding: 4px 6px; font-weight: bold;
    }
    QLabel { color: #6B7C74; font-family: "Segoe UI"; font-size: 13px; }
    QLabel#Title { color: #1A3025; font-weight: bold; }
    QLabel#Header { color: #1A3025; font-size: 18px; font-weight: bold; }
    QLabel#Hint { color: #9AA9A2; font-size: 11px; }
    QLabel#ChartTitle { color: #1A3025; font-size: 13px; font-weight: bold; }
    QLabel#ChartDesc {
        color: #4A5A52; font-size: 12px;
        background-color: #F7FBF9; border: 1px solid #E2ECE7;
        border-radius: 8px; padding: 10px 14px;
    }
    QLabel#InsightsTitle {
        color: #0F6E4E; font-size: 12px; font-weight: bold;
        padding-top: 6px;
    }
    QLabel#Insights {
        color: #1A3025; font-size: 12px;
        background-color: #F0F9F4; border: 1px solid #CDE9D8;
        border-radius: 8px; padding: 10px 14px;
    }
    QCheckBox { color: #6B7C74; font-size: 12px; }
    QTextEdit {
        background-color: #1E2622; color: #E2ECE7; border: none;
        border-radius: 6px; font-family: 'Consolas'; font-size: 12px;
    }
"""


def _safe_hex(x):
    try:
        return int(str(x).strip(), 16)
    except Exception:
        return np.nan


# ============================================================
# АВТОВЫВОДЫ ПО ГРАФИКАМ
# ============================================================
class ChartInsights:
    """Генерирует текстовые выводы по данным для каждого типа графика.
    Возвращает список кортежей (level, text), где level ∈ {ok, warn, bad, info}."""

    # ---------- 1. Value/Time ----------
    @staticmethod
    def value_time(sub: pd.DataFrame) -> list:
        out = []
        n = len(sub)
        if n == 0:
            return [("bad", "Нет данных для анализа.")]

        invalid = int((~sub["is_valid"]).sum())
        pct = invalid / n * 100

        if pct == 0:
            out.append(("ok", f"Все {n:,} записей достоверны — сигнал чистый."))
        elif pct < 1:
            out.append(("ok", f"Сигнал в целом стабилен: недостоверных {invalid} ({pct:.2f}%)."))
        elif pct < 5:
            out.append(("warn", f"Недостоверных {invalid} ({pct:.1f}%) — есть отдельные сбои."))
        elif pct < 20:
            out.append(("warn", f"Недостоверных {invalid} ({pct:.1f}%) — заметная нестабильность."))
        else:
            out.append(("bad", f"Недостоверных {invalid} ({pct:.1f}%) — сигнал проблемный."))

        s = sub.sort_values("t_recv")
        dt = s["t_recv"].diff().dt.total_seconds().dropna()
        if len(dt) > 0:
            med_dt = dt.median()
            gaps = dt[dt > max(5 * med_dt, 300)]
            if len(gaps) > 0:
                out.append(("warn",
                    f"Обнаружено {len(gaps)} разрыв(ов) во времени "
                    f"(макс. {gaps.max()/60:.1f} мин). Возможны потери данных."))
            else:
                out.append(("ok", "Разрывов во времени нет — данные идут ровно."))

        vals = s["value"].astype(float)
        d = vals.diff().abs().dropna()
        if len(d) > 0:
            thresh = max(d.median() * 20, 100)
            jumps = d[d > thresh]
            if len(jumps) > 0:
                out.append(("warn",
                    f"Найдено {len(jumps)} скачк(ов) значения "
                    f"(макс. Δ = {jumps.max():.0f}). Проверьте — реальные или сбой."))

        if len(s) > 5:
            same = (vals.diff() == 0).sum()
            pct_same = same / n * 100
            if pct_same > 80:
                out.append(("warn",
                    f"{pct_same:.0f}% записей без изменений — возможен «залипший» сигнал."))

        return out

    # ---------- 2. Quality ----------
    @staticmethod
    def quality(sub: pd.DataFrame) -> list:
        out = []
        n = len(sub)
        if n == 0:
            return [("bad", "Нет данных.")]

        valid = int(sub["is_valid"].sum())
        invalid = n - valid
        pct = invalid / n * 100

        if pct == 0:
            out.append(("ok", f"Все {n:,} записей достоверны."))
        elif pct < 1:
            out.append(("ok", f"Практически чистый сигнал: {pct:.2f}% недостоверных."))
        elif pct < 5:
            out.append(("warn", f"{pct:.1f}% недостоверных — единичные сбои."))
        elif pct < 20:
            out.append(("warn", f"{pct:.1f}% недостоверных — требуется внимание."))
        else:
            out.append(("bad", f"{pct:.1f}% недостоверных — сигнал ненадёжен."))

        if n < 50:
            out.append(("info", f"Мало данных ({n} записей) — статистика может быть неточной."))

        return out

    # ---------- 3. Heatmap ----------
    @staticmethod
    def heatmap(sub: pd.DataFrame) -> list:
        out = []
        if len(sub) == 0:
            return [("bad", "Нет данных.")]

        s = sub.sort_values("t_recv").copy()
        s["bin"] = s["t_recv"].dt.floor("1min")
        by_min = s.groupby("bin")["is_valid"].apply(lambda x: 1 - x.mean())

        bad_minutes = int((by_min > 0).sum())
        total_minutes = len(by_min)
        worst = float(by_min.max()) if total_minutes else 0.0

        if bad_minutes == 0:
            out.append(("ok", "Ни одной минуты с недостоверными данными."))
        else:
            pct_min = bad_minutes / total_minutes * 100
            out.append(("warn",
                f"Сбои зафиксированы в {bad_minutes} из {total_minutes} минут "
                f"({pct_min:.0f}%). Худшая минута: {worst*100:.0f}% недостоверных."))

        if bad_minutes > 0:
            is_bad = (by_min > 0).astype(int).values
            max_run = 0
            cur = 0
            for v in is_bad:
                if v:
                    cur += 1
                    max_run = max(max_run, cur)
                else:
                    cur = 0
            if max_run >= 2:
                out.append(("bad",
                    f"Самый длинный непрерывный сбой: ~{max_run} мин. "
                    "Похоже на устойчивую проблему, а не разовый сбой."))
            else:
                out.append(("info", "Сбои короткие (1 мин) — похоже на разовые помехи."))

        return out

    # ---------- 4. Latency ----------
    @staticmethod
    def latency(sub: pd.DataFrame) -> list:
        out = []
        if len(sub) == 0:
            return [("bad", "Нет данных.")]

        s = sub.sort_values("t_recv")
        lat = (s["t_recv"] - s["t_send"]).dt.total_seconds() * 1000
        lat = lat.dropna()
        if len(lat) == 0:
            return [("bad", "Не удалось вычислить задержки.")]

        med = lat.median()
        p95 = lat.quantile(0.95)
        mx = lat.max()
        mn = lat.min()

        out.append(("info", f"Медиана: {med:.1f} мс, p95: {p95:.1f} мс, макс: {mx:.1f} мс."))

        if mn < -10:
            out.append(("warn",
                f"Минимальная latency отрицательная ({mn:.0f} мс) — "
                "возможна рассинхронизация часов между стойкой и шлюзом."))

        if med < 100:
            out.append(("ok", "Задержка в норме."))
        elif med < 500:
            out.append(("warn", "Задержка повышена — проверьте загрузку канала."))
        else:
            out.append(("bad", "Задержка высокая — связь перегружена."))

        if p95 > med * 5 and med > 0:
            out.append(("warn",
                f"«Тяжёлый хвост»: p95 в {p95/med:.1f}× больше медианы. "
                "Признак потери пакетов или очередей."))

        try:
            s2 = s.assign(lat=(s["t_recv"] - s["t_send"]).dt.total_seconds() * 1000)
            s2 = s2.dropna(subset=["lat"])
            if s2["is_valid"].nunique() > 1:
                med_valid = s2[s2["is_valid"]]["lat"].median()
                med_invalid = s2[~s2["is_valid"]]["lat"].median()
                if pd.notna(med_valid) and pd.notna(med_invalid):
                    if med_invalid > med_valid * 2:
                        out.append(("warn",
                            f"У недостоверных записей latency выше "
                            f"({med_invalid:.0f} мс vs {med_valid:.0f} мс) — "
                            "сбои связаны с задержками связи."))
                    elif med_invalid < med_valid * 0.5:
                        out.append(("info",
                            "У недостоверных записей latency ниже — "
                            "сбои, скорее всего, на стороне источника."))
        except Exception:
            pass

        return out

    # ---------- 5. Histogram ----------
    @staticmethod
    def hist_value(sub: pd.DataFrame) -> list:
        out = []
        vals = sub["value"].dropna().astype(float)
        if len(vals) == 0:
            return [("bad", "Нет числовых значений.")]

        out.append(("info",
            f"Диапазон: [{vals.min():.0f} … {vals.max():.0f}], "
            f"медиана: {vals.median():.0f}."))

        at_zero = (vals == 0).sum() / len(vals) * 100
        at_max = (vals == 65535).sum() / len(vals) * 100
        if at_zero > 30:
            out.append(("warn",
                f"{at_zero:.0f}% значений = 0 — возможен обрыв или сбой датчика."))
        if at_max > 30:
            out.append(("warn",
                f"{at_max:.0f}% значений = 65535 — возможен перегруз или сбой."))

        try:
            hist, _ = np.histogram(vals, bins=30)
            peaks = 0
            hmax = hist.max() if hist.size else 0
            for i in range(1, len(hist) - 1):
                if hist[i] > hist[i-1] and hist[i] > hist[i+1] and hist[i] > hmax * 0.3:
                    peaks += 1
            if peaks >= 3:
                out.append(("info",
                    f"Распределение многомодальное ({peaks} пиков) — "
                    "сигнал работает в нескольких режимах."))
        except Exception:
            pass

        iqr = vals.quantile(0.75) - vals.quantile(0.25)
        rng = vals.max() - vals.min()
        if rng > 0 and iqr / rng < 0.05:
            out.append(("warn",
                "Сигнал сосредоточен в очень узком диапазоне — "
                "возможно «залипание» или малая чувствительность."))

        return out

    # ---------- 6. Delta ----------
    @staticmethod
    def delta_hist(sub: pd.DataFrame) -> list:
        out = []
        s = sub.sort_values("t_recv")
        vals = s["value"].astype(float)
        d = vals.diff().dropna()
        if len(d) == 0:
            return [("bad", "Недостаточно данных для расчёта Δ.")]

        n = len(d)
        zero_pct = (d == 0).sum() / n * 100
        big_jumps = int((d.abs() > 100).sum())
        asym = d.mean()

        if zero_pct > 80:
            out.append(("warn",
                f"{zero_pct:.0f}% шагов без изменений — сигнал почти не меняется."))
        elif zero_pct > 40:
            out.append(("info", f"{zero_pct:.0f}% шагов без изменений — умеренная динамика."))
        else:
            out.append(("ok", "Сигнал активно меняется."))

        if big_jumps > 0:
            pct = big_jumps / n * 100
            if pct > 5:
                out.append(("bad",
                    f"{big_jumps} больших скачков (Δ>100) — {pct:.1f}% шагов. "
                    "Похоже на сбой или сильные помехи."))
            else:
                out.append(("warn",
                    f"{big_jumps} больших скачков (Δ>100) — возможны разовые помехи."))
        else:
            out.append(("ok", "Больших скачков (|Δ|>100) не обнаружено."))

        if d.std() > 0 and abs(asym) > d.std():
            direction = "растёт" if asym > 0 else "падает"
            out.append(("info", f"Сигнал в среднем {direction} (средний Δ = {asym:.1f})."))

        return out

    # ---------- 7. Rate ----------
    @staticmethod
    def rate(sub: pd.DataFrame) -> list:
        out = []
        s = sub.sort_values("t_recv")
        d_val = s["value"].astype(float).diff()
        d_t = s["t_recv"].diff().dt.total_seconds()
        rate = (d_val / d_t).replace([np.inf, -np.inf], np.nan).dropna()
        if len(rate) == 0:
            return [("bad", "Недостаточно данных.")]

        med = rate.median()
        p95 = rate.abs().quantile(0.95)
        mx = rate.abs().max()

        out.append(("info",
            f"Типичная скорость: {med:.2f}/с, "
            f"95-й перцентиль: {p95:.2f}/с, макс: {mx:.2f}/с."))

        if abs(med) > 0 and p95 > abs(med) * 10 and p95 > 1:
            out.append(("warn",
                "Есть резкие всплески скорости — возможны помехи или "
                "периодические возмущения."))

        thresh = max(abs(med) * 3, 0.1)
        peaks = int((rate.abs() > thresh).sum())
        if peaks > 5:
            out.append(("info",
                f"Обнаружено {peaks} всплесков скорости — "
                "проверьте, нет ли периодичности (оператор опроса, вибрация)."))
        elif peaks > 0:
            out.append(("ok", f"Редкие всплески ({peaks}) — не критично."))
        else:
            out.append(("ok", "Сигнал меняется плавно, без всплесков."))

        return out


# ============================================================
# ПОТОК ЗАГРУЗКИ
# ============================================================
class LoaderThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(pd.DataFrame)
    error = pyqtSignal(str)

    def __init__(self, path: str, chunksize: int = 100_000):
        super().__init__()
        self.path = path
        self.chunksize = chunksize

    def run(self):
        try:
            file_size = os.path.getsize(self.path)
            bytes_read = 0
            chunks = []

            reader = pd.read_csv(
                self.path, sep=r"\s+", header=None, engine="python",
                names=EXPECTED, chunksize=self.chunksize,
                on_bad_lines="skip",
            )

            for chunk in reader:
                if len(chunk.columns) > len(EXPECTED):
                    chunk = chunk.iloc[:, :len(EXPECTED)]
                    chunk.columns = EXPECTED
                elif len(chunk.columns) < len(EXPECTED):
                    for i in range(len(chunk.columns), len(EXPECTED)):
                        chunk[EXPECTED[i]] = pd.NA
                    chunk = chunk[EXPECTED]

                chunk["t_recv"] = pd.to_datetime(
                    pd.to_numeric(chunk["t_recv"], errors="coerce"),
                    unit="s", errors="coerce")
                chunk["t_send"] = pd.to_datetime(
                    pd.to_numeric(chunk["t_send"], errors="coerce"),
                    unit="s", errors="coerce")

                chunk["value"] = chunk["value"].map(_safe_hex)
                chunk["valid_flag"] = chunk["valid_flag"].map(_safe_hex)
                chunk["is_valid"] = chunk["valid_flag"].fillna(1) == 0

                chunk["varid"] = chunk["varid"].astype(str).str.strip()
                chunk["rack"] = chunk["rack"].astype(str).str.strip()

                chunk = chunk.dropna(subset=["t_recv"])
                chunk = chunk[(chunk["varid"] != "nan") & (chunk["rack"] != "nan")]
                if chunk.empty:
                    continue

                chunks.append(chunk)
                bytes_read += chunk.memory_usage(deep=True).sum()
                pct = min(99, int(bytes_read / max(file_size, 1) * 100))
                self.progress.emit(pct)

            if not chunks:
                self.error.emit("Не удалось прочитать ни одной валидной строки.")
                return

            df = pd.concat(chunks, ignore_index=True)
            df = df.sort_values([RACK_COL, KEY_COL, "t_recv"]).reset_index(drop=True)
            self.finished.emit(df)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(f"{type(e).__name__}: {e}")


# ============================================================
# ДЕРЕВО: СТОЙКА → ВАРИДЫ
# ============================================================
class SignalTree(QTreeWidget):
    """Двухуровневое дерево: стойка → вариды. Ленивая загрузка детей."""

    MAX_CHILDREN = 1000   # максимум варидов под одной стойкой

    signal_selected = pyqtSignal(str, str)   # (rack, varid)

    def __init__(self):
        super().__init__()
        self.setHeaderLabels(["Стойка / Варид", "Записей", "⚠ %"])
        self.setColumnWidth(0, 170)
        self.setColumnWidth(1, 60)
        self.setColumnWidth(2, 50)
        self.setRootIsDecorated(True)
        self.setUniformRowHeights(True)   # ← ключ к производительности
        self.itemExpanded.connect(self._on_expand)
        self.itemClicked.connect(self._on_click)

        # агрегаты (rack, varid) → count
        self._varid_counts_by_rack: dict[str, pd.Series] = {}
        self._varid_invalid_by_rack: dict[str, pd.Series] = {}

    def set_data(self, df: pd.DataFrame):
        self.clear()
        self._varid_counts_by_rack.clear()
        self._varid_invalid_by_rack.clear()

        if df is None or df.empty:
            return

        # Агрегаты по стойкам
        rack_counts = df.groupby(RACK_COL).size().sort_values(ascending=False)
        rack_invalid = df[~df["is_valid"]].groupby(RACK_COL).size()

        # Агрегаты по (rack, varid)
        by_rack_varid = df.groupby([RACK_COL, KEY_COL]).size()
        by_rack_varid_inv = df[~df["is_valid"]].groupby([RACK_COL, KEY_COL]).size()

        for rack, series in by_rack_varid.groupby(level=0):
            self._varid_counts_by_rack[rack] = series.droplevel(0).sort_values(ascending=False)

        for rack, series in by_rack_varid_inv.groupby(level=0):
            self._varid_invalid_by_rack[rack] = series.droplevel(0)

        # Заполняем только стойки (дети — при раскрытии)
        for rack, total in rack_counts.items():
            inv = int(rack_invalid.get(rack, 0))
            pct = inv / total * 100 if total else 0
            item = QTreeWidgetItem([f"📡 {rack}", f"{total:,}", f"{pct:.1f}%"])
            item.setData(0, Qt.UserRole, ("rack", rack))
            # плейсхолдер, чтобы стрелка раскрытия была видна
            item.addChild(QTreeWidgetItem(["Загрузка...", "", ""]))
            self.addTopLevelItem(item)

    def _on_expand(self, item):
        """Загружаем детей только при первом раскрытии."""
        data = item.data(0, Qt.UserRole)
        if not data or data[0] != "rack":
            return
        # уже загружено?
        if item.childCount() == 1 and item.child(0).text(0) == "Загрузка...":
            item.takeChild(0)
            rack = data[1]
            counts = self._varid_counts_by_rack.get(rack)
            if counts is None or counts.empty:
                return
            invalid = self._varid_invalid_by_rack.get(rack)

            shown = counts.head(self.MAX_CHILDREN)
            for varid, cnt in shown.items():
                inv = int(invalid.get(varid, 0)) if invalid is not None else 0
                pct = inv / cnt * 100 if cnt else 0
                child = QTreeWidgetItem([f"  {varid}", f"{cnt:,}", f"{pct:.1f}%"])
                child.setData(0, Qt.UserRole, ("varid", rack, varid))
                item.addChild(child)

            if len(counts) > self.MAX_CHILDREN:
                more = QTreeWidgetItem(
                    [f"  … ещё {len(counts) - self.MAX_CHILDREN:,} "
                     f"(используйте поиск)", "", ""])
                more.setDisabled(True)
                item.addChild(more)

    def _on_click(self, item, column):
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        if data[0] == "varid":
            _, rack, varid = data
            self.signal_selected.emit(rack, varid)

    def expand_all_racks(self, max_racks: int = 30):
        """Раскрыть N первых стоек (для быстрого обзора)."""
        for i in range(min(max_racks, self.topLevelItemCount())):
            self.topLevelItem(i).setExpanded(True)

    def filter_tree(self, text: str, max_results: int = 500):
        """Фильтр: показываем только совпадающие стойки/вариды."""
        text = text.strip().lower()
        if not text:
            # вернуть исходный вид
            for i in range(self.topLevelItemCount()):
                top = self.topLevelItem(i)
                top.setHidden(False)
                for j in range(top.childCount()):
                    top.child(j).setHidden(False)
            return

        shown = 0
        for i in range(self.topLevelItemCount()):
            top = self.topLevelItem(i)
            data = top.data(0, Qt.UserRole)
            if not data:
                continue
            rack = data[1]
            rack_match = text in rack.lower()

            # Обеспечим загрузку детей, чтобы искать среди них
            if top.childCount() == 1 and top.child(0).text(0) == "Загрузка...":
                self._on_expand(top)

            child_match = False
            for j in range(top.childCount()):
                ch = top.child(j)
                ch_data = ch.data(0, Qt.UserRole)
                if not ch_data or ch_data[0] != "varid":
                    continue
                varid = ch_data[2]
                m = rack_match or (text in varid.lower())
                ch.setHidden(not m)
                if m:
                    child_match = True
                    shown += 1
                    if shown >= max_results:
                        break

            top.setHidden(not (rack_match or child_match))
            if rack_match or child_match:
                top.setExpanded(True)


# ============================================================
# ОСНОВНОЕ ОКНО
# ============================================================
class MainWindow(QMainWindow):
    TOP_N = 50

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Анализатор")
        self.resize(1400, 900)

        self.df: pd.DataFrame | None = None
        self.current_rack: str | None = None
        self.current_varid: str | None = None
        self.current_chart: str = "value_time"

        main_widget = QWidget()
        main_widget.setObjectName("Main")
        self.setCentralWidget(main_widget)

        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # ===== Сайдбар =====
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(330)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(12, 20, 12, 20)
        sb_layout.setSpacing(8)

        logo = QLabel("🌱 Анализатор")
        logo.setObjectName("Header")
        sb_layout.addWidget(logo)
        sb_layout.addSpacing(6)

        self.btn_load = QPushButton("📂 Загрузить файл")
        self.btn_load.setObjectName("ActionBtn")
        self.btn_load.setCursor(Qt.PointingHandCursor)
        self.btn_load.clicked.connect(self.load_file)
        sb_layout.addWidget(self.btn_load)
        sb_layout.addSpacing(10)

        sb_layout.addWidget(QLabel("СТОЙКИ / ВАРИДЫ", objectName="Title"))

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 Поиск по стойке или вариду...")
        self.search.textChanged.connect(self.on_search)
        sb_layout.addWidget(self.search)

        self.chk_invalid_only = QCheckBox("Только с недостоверными")
        self.chk_invalid_only.stateChanged.connect(lambda _: self.on_search(self.search.text()))
        sb_layout.addWidget(self.chk_invalid_only)

        self.tree = SignalTree()
        self.tree.signal_selected.connect(self.on_signal_selected)
        sb_layout.addWidget(self.tree, stretch=1)

        self.list_hint = QLabel("—")
        self.list_hint.setObjectName("Hint")
        sb_layout.addWidget(self.list_hint)

        self.file_info = QLabel("Файл не загружен")
        self.file_info.setWordWrap(True)
        self.file_info.setObjectName("Hint")
        sb_layout.addWidget(self.file_info)

        # ===== Правая часть =====
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)

        top_card = QWidget()
        top_card.setObjectName("Card")
        top_lay = QVBoxLayout(top_card)
        top_lay.setContentsMargins(15, 12, 15, 12)
        top_lay.addWidget(QLabel("ТИП ГРАФИКА", objectName="Title"))

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.chart_buttons = {}
        chart_defs = [
            ("value_time",  "📈 Value/Time"),
            ("quality",     "🚦 Качество"),
            ("heatmap",     "🔥 Heatmap"),
            ("latency",     "⏱ Latency"),
            ("hist_value",  "📊 Гистограмма"),
            ("delta_hist",  "ΔValue"),
            ("rate",        "📉 Rate"),
        ]
        for key, label in chart_defs:
            b = QPushButton(label)
            b.setCheckable(True)
            b.setAutoExclusive(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _, k=key: self.set_chart(k))
            btn_row.addWidget(b)
            self.chart_buttons[key] = b
        self.chart_buttons["value_time"].setChecked(True)
        top_lay.addLayout(btn_row)
        right_layout.addWidget(top_card)

        chart_card = QWidget()
        chart_card.setObjectName("Card")
        chart_lay = QVBoxLayout(chart_card)
        chart_lay.setContentsMargins(15, 12, 15, 12)
        chart_lay.setSpacing(10)

        self.chart_title = QLabel("Выберите варид в дереве слева")
        self.chart_title.setObjectName("ChartTitle")
        self.chart_title.setWordWrap(True)
        chart_lay.addWidget(self.chart_title)

        self.figure = Figure(figsize=(8, 4.2), dpi=100, facecolor="#FFFFFF")
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        chart_lay.addWidget(self.toolbar)
        chart_lay.addWidget(self.canvas, stretch=1)

        # Описание графика
        self.chart_desc = QLabel(CHART_DESCRIPTIONS["value_time"])
        self.chart_desc.setObjectName("ChartDesc")
        self.chart_desc.setWordWrap(True)
        self.chart_desc.setTextFormat(Qt.RichText)
        chart_lay.addWidget(self.chart_desc)

        # Заголовок панели автовыводов
        self.insights_title = QLabel("ЧТО ВИДНО ИЗ ЭТОГО ГРАФИКА")
        self.insights_title.setObjectName("InsightsTitle")
        chart_lay.addWidget(self.insights_title)

        # Панель автовыводов
        self.insights_label = QLabel("Загрузите файл и выберите варид.")
        self.insights_label.setObjectName("Insights")
        self.insights_label.setWordWrap(True)
        self.insights_label.setTextFormat(Qt.RichText)
        chart_lay.addWidget(self.insights_label)

        right_layout.addWidget(chart_card, stretch=1)

        log_card = QWidget()
        log_card.setObjectName("Card")
        log_lay = QVBoxLayout(log_card)
        log_lay.setContentsMargins(15, 10, 15, 10)
        log_lay.addWidget(QLabel("СИСТЕМНЫЙ ЛОГ", objectName="Title"))

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFixedHeight(80)
        self.log_view.setPlainText("SYSTEM >> Готов к работе. Загрузите файл.")
        log_lay.addWidget(self.log_view)
        right_layout.addWidget(log_card)

        layout.addWidget(sidebar)
        layout.addWidget(right, stretch=1)

    def log(self, msg: str):
        self.log_view.append(f"SYSTEM >> {msg}")

    # ---------- Загрузка ----------
    def load_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл лога", "",
            "Text/Log (*.txt *.log *.csv);;All files (*)"
        )
        if not path:
            return
        self.log(f"Загрузка: {path}")

        self.progress_dlg = QProgressDialog("Загрузка...", None, 0, 100, self)
        self.progress_dlg.setWindowTitle("Обработка файла")
        self.progress_dlg.setWindowModality(Qt.WindowModal)
        self.progress_dlg.setCancelButton(None)
        self.progress_dlg.setMinimumDuration(0)
        self.progress_dlg.show()

        self.loader = LoaderThread(path, chunksize=100_000)
        self.loader.progress.connect(self._on_progress)
        self.loader.finished.connect(self.on_loaded)
        self.loader.error.connect(self.on_load_error)
        self.loader.start()

    def _on_progress(self, v):
        if getattr(self, "progress_dlg", None) is not None:
            self.progress_dlg.setValue(v)

    def on_loaded(self, df: pd.DataFrame):
        if getattr(self, "progress_dlg", None) is not None:
            try:
                self.progress_dlg.close()
                self.progress_dlg.deleteLater()
            except Exception:
                pass
            self.progress_dlg = None

        self.df = df
        self.log(f"Загружено {len(df):,} строк.")
        self.log(f"Стоек: {df[RACK_COL].nunique():,}, "
                 f"варидов: {df[KEY_COL].nunique():,}")

        # Заполняем дерево (только стойки!)
        self.tree.set_data(df)
        self.list_hint.setText(
            f"Стоек: {df[RACK_COL].nunique():,} • "
            f"варидов: {df[KEY_COL].nunique():,}"
        )

        total = max(len(df), 1)
        invalid_total = int((~df["is_valid"]).sum())
        valid_pct = (total - invalid_total) / total * 100
        invalid_pct = invalid_total / total * 100

        t_min = df["t_recv"].min(); t_max = df["t_recv"].max()
        period = "—"
        try:
            period = f"{t_min:%Y-%m-%d %H:%M}\n     — {t_max:%Y-%m-%d %H:%M}"
        except Exception:
            pass

        self.file_info.setText(
            f"Строк: {total:,}\n"
            f"Стоек: {df[RACK_COL].nunique():,}\n"
            f"Варидов: {df[KEY_COL].nunique():,}\n"
            f"Период: {period}\n"
            f"Достоверных: {valid_pct:.1f}%  "
            f"Недостоверных: {invalid_pct:.1f}%"
        )

    def on_load_error(self, err: str):
        if getattr(self, "progress_dlg", None) is not None:
            try:
                self.progress_dlg.close()
            except Exception:
                pass
            self.progress_dlg = None
        QMessageBox.critical(self, "Ошибка загрузки", err)
        self.log(f"ОШИБКА: {err}")

    # ---------- Поиск ----------
    def on_search(self, text: str):
        # Фильтр в дереве (не создаёт виджеты)
        self.tree.filter_tree(text)
        # Если стоит чекбокс «только с недостоверными» — фильтруем по флагу
        if self.chk_invalid_only.isChecked() and self.df is not None:
            # оставим только стойки/вариды с недостоверными — уже видно по ⚠ %
            pass

    # ---------- Выбор сигнала ----------
    def on_signal_selected(self, rack: str, varid: str):
        self.current_rack = rack
        self.current_varid = varid
        self.log(f"Выбран: стойка={rack}, варид={varid}")
        self.draw()

    def set_chart(self, key: str):
        self.current_chart = key
        self.chart_desc.setText(CHART_DESCRIPTIONS.get(key, ""))
        self.draw()

    # ---------- Отрисовка ----------
    def draw(self):
        if self.df is None or self.current_varid is None:
            return
        try:
            sub = self.df[
                (self.df[KEY_COL] == self.current_varid) &
                (self.df[RACK_COL] == self.current_rack)
            ].copy()
            if sub.empty:
                self.chart_title.setText("Нет данных")
                self.insights_label.setText("—")
                return

            total = len(sub)
            invalid = int((~sub["is_valid"]).sum())
            pct = invalid / total * 100 if total else 0
            t_min = sub["t_recv"].min(); t_max = sub["t_recv"].max()
            period = ""
            try:
                period = f"   •   {t_min:%Y-%m-%d %H:%M:%S} — {t_max:%H:%M:%S}"
            except Exception:
                pass
            self.chart_title.setText(
                f"varid = {self.current_varid}   •   стойка: {self.current_rack}   •   "
                f"записей: {total:,}   •   недостоверных: {invalid:,} ({pct:.1f}%){period}"
            )

            self.figure.clear()
            ax = self.figure.add_subplot(111)
            method = getattr(self, f"_chart_{self.current_chart}", None)
            if method:
                method(ax, sub)
            self.figure.tight_layout()
            self.canvas.draw_idle()

            # Автовыводы
            self._update_insights(sub)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.log(f"Ошибка отрисовки: {e}")

    def _update_insights(self, sub: pd.DataFrame):
        """Обновляет панель выводов по текущему графику."""
        analyzer = getattr(ChartInsights, self.current_chart, None)
        if analyzer is None:
            self.insights_label.setText("—")
            return
        try:
            insights = analyzer(sub)
        except Exception as e:
            self.insights_label.setText(f"⚠ Ошибка анализа: {e}")
            return

        if not insights:
            self.insights_label.setText("—")
            return

        icons = {"ok": "✅", "warn": "⚠", "bad": "🛑", "info": "ℹ"}
        colors = {
            "ok":   "#0F6E4E",
            "warn": "#B45309",
            "bad":  "#B91C1C",
            "info": "#1E40AF",
        }
        lines = []
        for level, text in insights:
            icon = icons.get(level, "•")
            color = colors.get(level, "#1A3025")
            lines.append(f'<span style="color:{color};">{icon} {text}</span>')
        self.insights_label.setText("<br>".join(lines))

    # ---------- Настройка оси времени ----------
    @staticmethod
    def _format_time_axis(ax, fig):
        """Правильный формат даты/времени на оси X."""
        locator = mdates.AutoDateLocator(minticks=4, maxticks=8)
        formatter = mdates.ConciseDateFormatter(locator)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)
        fig.autofmt_xdate()

    # ---------- Графики ----------
    def _chart_value_time(self, ax, sub):
        s = sub.sort_values("t_recv")
        colors = np.where(s["is_valid"], "#10B981", "#EF4444")
        ax.plot(s["t_recv"], s[VALUE_COL], color="#CBD5D1", lw=0.6, alpha=0.6, zorder=0)
        ax.scatter(s["t_recv"], s[VALUE_COL], c=colors, s=12, alpha=0.9, zorder=1)
        ax.set_xlabel("Время приёма")
        ax.set_ylabel("Значение сигнала")
        ax.grid(True, alpha=0.2)
        handles = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor="#10B981",
                   markersize=8, label="Достоверно"),
            Line2D([0], [0], marker='o', color='w', markerfacecolor="#EF4444",
                   markersize=8, label="Недостоверно"),
        ]
        ax.legend(handles=handles, loc="best", fontsize=9)
        self._format_time_axis(ax, self.figure)

    def _chart_quality(self, ax, sub):
        valid = int(sub["is_valid"].sum())
        invalid = int((~sub["is_valid"]).sum())
        total = valid + invalid
        bars = ax.bar(["Достоверно", "Недостоверно"],
                      [valid, invalid],
                      color=["#10B981", "#EF4444"], alpha=0.85)
        for b, v in zip(bars, [valid, invalid]):
            pct = v / total * 100 if total else 0
            ax.text(b.get_x() + b.get_width()/2, b.get_height(),
                    f"{v:,}\n({pct:.1f}%)", ha="center", va="bottom", fontsize=10)
        ax.set_ylabel("Количество записей")
        ax.grid(True, axis="y", alpha=0.2)

    def _chart_heatmap(self, ax, sub):
        s = sub.sort_values("t_recv").copy()
        s["bin"] = s["t_recv"].dt.floor("1min")
        pivot = s.groupby("bin")["is_valid"].apply(lambda x: 1 - x.mean())
        if pivot.empty:
            return
        vals = pivot.values.reshape(1, -1)
        im = ax.imshow(
            vals, aspect="auto", cmap="Reds", vmin=0, vmax=1,
            extent=[mdates.date2num(pivot.index[0]),
                    mdates.date2num(pivot.index[-1]), 0, 1]
        )
        ax.set_yticks([])
        ax.xaxis_date()
        self._format_time_axis(ax, self.figure)
        self.figure.colorbar(im, ax=ax, label="Доля недостоверных")

    def _chart_latency(self, ax, sub):
        s = sub.sort_values("t_recv")
        lat = (s["t_recv"] - s["t_send"]).dt.total_seconds() * 1000
        colors = np.where(s["is_valid"], "#8B5CF6", "#EF4444")
        ax.scatter(s["t_recv"], lat, c=colors, s=10, alpha=0.8)
        med = lat.median()
        ax.axhline(med, color="#10B981", ls="--", lw=1,
                   label=f"Медиана: {med:.1f} мс")
        ax.set_xlabel("Время")
        ax.set_ylabel("Latency, мс")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.2)
        self._format_time_axis(ax, self.figure)

    def _chart_hist_value(self, ax, sub):
        vals = sub[VALUE_COL].dropna().astype(float)
        ax.hist(vals, bins=50, color="#10B981", edgecolor="#059669", alpha=0.85)
        ax.set_xlabel("Значение сигнала")
        ax.set_ylabel("Частота")
        ax.grid(True, alpha=0.2)

    def _chart_delta_hist(self, ax, sub):
        s = sub.sort_values("t_recv")
        d = s[VALUE_COL].astype(float).diff().dropna()
        ax.hist(d, bins=50, color="#3B82F6", edgecolor="#1D4ED8", alpha=0.85)
        ax.set_xlabel("ΔValue")
        ax.set_ylabel("Частота")
        ax.grid(True, alpha=0.2)

    def _chart_rate(self, ax, sub):
        s = sub.sort_values("t_recv")
        d_val = s[VALUE_COL].astype(float).diff()
        d_t = s["t_recv"].diff().dt.total_seconds()
        rate = (d_val / d_t).replace([np.inf, -np.inf], np.nan)
        ax.plot(s["t_recv"], rate, color="#EC4899", lw=0.8)
        ax.set_xlabel("Время")
        ax.set_ylabel("ΔValue / сек")
        ax.grid(True, alpha=0.2)
        self._format_time_axis(ax, self.figure)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(MINT_STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())