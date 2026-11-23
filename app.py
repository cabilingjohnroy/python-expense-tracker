"""FlowMoney 4.0 — charcoal / royal blue / tangerine expense tracker.

Requires: customtkinter, and the project's existing database.py module.
"""
from datetime import date, datetime
from collections import defaultdict
import csv
from tkinter import filedialog
from decimal import Decimal, InvalidOperation
import tkinter as tk

import customtkinter as ctk

from database import (
    create_database,
    add_transaction,
    get_transactions,
    delete_transaction,
    get_totals,
    get_categories,
)
from reports import (
    category_choices,
    month_label,
    monthly_totals,
    normalize_category,
    records_in_month,
    shift_month,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Brand palette — requested by the user
BG = "#21232E"             # Charcoal black
ACCENT = "#105BFF"         # Royal blue
ORANGE = "#FE8500"         # Tangerine orange

# Supporting neutral surfaces (not competing brand colors)
SIDEBAR = "#191B25"
PANEL = "#292C3A"
PANEL_2 = "#323645"
BORDER = "#3B4050"
FIELD = "#20232E"
WHITE = "#F9FAFF"
MUTED = "#A6AAB9"
ACCENT_HOVER = "#0048DC"
ORANGE_HOVER = "#DB7100"
GREEN = "#53D9A7"
RED = "#FF7287"
FONT = "Segoe UI"


def peso(amount):
    value = float(amount)
    sign = "-" if value < 0 else ""
    return f"{sign}₱{abs(value):,.2f}"


class FlowMoney(ctk.CTk):
    def __init__(self):
        super().__init__()
        create_database()
        self.title("FlowMoney  |  Personal finance")
        self.geometry("1240x800")
        self.minsize(980, 660)
        self.configure(fg_color=BG)
        self.page = "dashboard"
        self.active_dialog = None
        self._search_job = None
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search)
        self.filter_type = tk.StringVar(value="All")
        # Report state lives here so it's remembered when you switch pages.
        self.report_mode = tk.StringVar(value="Monthly")
        self.report_month = date.today().replace(day=1)
        self._build_shell()
        self.show_dashboard()

    def _build_shell(self):
        self.sidebar = ctk.CTkFrame(self, width=238, fg_color=SIDEBAR, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=20, pady=(32, 6))
        ctk.CTkLabel(
            brand, text="F", width=42, height=42, fg_color=ACCENT, corner_radius=13,
            font=(FONT, 24, "bold"), text_color=WHITE
        ).pack(side="left")
        brand_words = ctk.CTkFrame(brand, fg_color="transparent")
        brand_words.pack(side="left", padx=(11, 0))
        ctk.CTkLabel(brand_words, text="FlowMoney", font=(FONT, 20, "bold"),
                     text_color=WHITE).pack(anchor="w")
        ctk.CTkLabel(brand_words, text="PERSONAL FINANCE", font=(FONT, 9, "bold"),
                     text_color=MUTED).pack(anchor="w")

        ctk.CTkLabel(self.sidebar, text="WORKSPACE", font=(FONT, 10, "bold"),
                     text_color=MUTED).pack(anchor="w", padx=24, pady=(50, 12))
        self.nav_dashboard = self._nav("▦     Overview", self.show_dashboard)
        self.nav_transactions = self._nav("≡     Transactions", self.show_transactions)
        self.nav_reports = self._nav("▤     Financial report", self.show_reports)

        ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER).pack(fill="x", padx=20, pady=26)
        tip = ctk.CTkFrame(self.sidebar, fg_color=PANEL, corner_radius=17,
                           border_width=1, border_color=BORDER)
        tip.pack(fill="x", padx=15)
        ctk.CTkLabel(tip, text="●  MONEY MATTERS", font=(FONT, 10, "bold"),
                     text_color=ORANGE).pack(anchor="w", padx=17, pady=(17, 9))
        ctk.CTkLabel(tip, text="A clearer view of your\nfinancial everyday.",
                     justify="left", font=(FONT, 12),
                     text_color=MUTED).pack(anchor="w", padx=17, pady=(0, 18))
        ctk.CTkLabel(self.sidebar, text="FLOWMONEY     /     V4.0", font=(FONT, 10),
                     text_color=MUTED).pack(side="bottom", pady=22)

        self.content = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.content.pack(fill="both", expand=True)

    def _nav(self, label, command):
        btn = ctk.CTkButton(self.sidebar, text=label, command=command, height=49, anchor="w", font=(FONT, 13, "bold"), fg_color="transparent", hover_color=PANEL_2, text_color=MUTED, corner_radius=11)
        btn.pack(fill="x", padx=14, pady=5)
        return btn

    def _activate_nav(self):
        for button, active in ((self.nav_dashboard, self.page == "dashboard"), (self.nav_transactions, self.page == "transactions"), (self.nav_reports, self.page == "reports")):
            button.configure(fg_color=ACCENT if active else "transparent", text_color=WHITE if active else MUTED)

    def _clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def _header(self, title, subtitle):
        bar = ctk.CTkFrame(self.content, fg_color="transparent")
        bar.pack(fill="x", padx=34, pady=(31, 23))
        heading = ctk.CTkFrame(bar, fg_color="transparent")
        heading.pack(side="left")
        ctk.CTkLabel(heading, text=title, font=(FONT, 30, "bold"),
                     text_color=WHITE).pack(anchor="w")
        ctk.CTkLabel(heading, text=subtitle, font=(FONT, 13),
                     text_color=MUTED).pack(anchor="w", pady=(5, 0))
        ctk.CTkButton(bar, text="+  New transaction", command=self.add_dialog,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER,
                      height=46, width=182, corner_radius=13,
                      font=(FONT, 13, "bold")).pack(side="right")

    def _card(self, parent, label, value, color, icon):
        card = ctk.CTkFrame(parent, fg_color=PANEL, border_color=BORDER,
                            border_width=1, corner_radius=19)
        card.pack(side="left", fill="both", expand=True, padx=7)
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(19, 17))
        ctk.CTkLabel(top, text=label.upper(), font=(FONT, 10, "bold"),
                     text_color=MUTED).pack(side="left")
        ctk.CTkLabel(top, text=icon, width=32, height=32, font=(FONT, 17, "bold"),
                     fg_color=PANEL_2, corner_radius=10, text_color=color).pack(side="right")
        ctk.CTkLabel(card, text=peso(value), font=(FONT, 25, "bold"),
                     text_color=color).pack(anchor="w", padx=20, pady=(0, 24))

    def _hero(self, balance, income, expenses):
        hero = ctk.CTkFrame(self.content, fg_color=ACCENT, corner_radius=21)
        hero.pack(fill="x", padx=33, pady=(0, 24))
        inner = ctk.CTkFrame(hero, fg_color="transparent")
        inner.pack(fill="x", padx=28, pady=23)
        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(left, text="YOUR FINANCIAL SNAPSHOT  /  ALL TIME",
                     text_color="#D6E4FF", font=(FONT, 10, "bold")).pack(anchor="w")
        ctk.CTkLabel(left, text="Make every peso count.", font=(FONT, 24, "bold"),
                     text_color=WHITE).pack(anchor="w", pady=(7, 4))
        ctk.CTkLabel(left, text="Track what comes in, understand what goes out.",
                     font=(FONT, 12), text_color="#D6E4FF").pack(anchor="w")
        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right", padx=(20, 0))
        ctk.CTkLabel(right, text="CURRENT BALANCE", font=(FONT, 10, "bold"),
                     text_color="#D6E4FF").pack(anchor="e")
        ctk.CTkLabel(right, text=peso(balance), font=(FONT, 29, "bold"),
                     text_color=WHITE).pack(anchor="e", pady=(4, 0))
        if income > 0:
            ratio = expenses / income * 100
            overspent = ratio > 100
            ctk.CTkLabel(right, text=f"{ratio:.0f}% of income spent" + ("  ·  over budget" if overspent else ""),
                         font=(FONT, 11, "bold" if overspent else "normal"),
                         text_color=ORANGE if overspent else "#D6E4FF").pack(anchor="e", pady=(2, 0))
        ctk.CTkFrame(hero, height=5, fg_color=ORANGE, corner_radius=0).pack(fill="x", padx=20, pady=(0, 0))

    def show_dashboard(self):
        self.page = "dashboard"
        self._clear_content()
        self._activate_nav()
        self._header("Overview", "Here's how your money is doing today.")
        income, expenses, balance = get_totals()
        self._hero(balance, income, expenses)
        cards = ctk.CTkFrame(self.content, fg_color="transparent")
        cards.pack(fill="x", padx=26, pady=(0, 24))
        self._card(cards, "Available balance", balance, WHITE, "◈")
        self._card(cards, "Total income", income, GREEN, "↗")
        self._card(cards, "Total expenses", expenses, ORANGE, "↘")
        self._render_transactions(self.content, get_transactions(limit=7), "Recent activity", show_all=True)

    def show_transactions(self):
        self.page = "transactions"
        self._clear_content()
        self._activate_nav()
        self._header("Transactions", "Every peso, in one place.")
        controls = ctk.CTkFrame(self.content, fg_color="transparent")
        controls.pack(fill="x", padx=32, pady=(0, 18))
        self.search_entry = ctk.CTkEntry(controls, textvariable=self.search_var, placeholder_text="Search by category, date or amount...", height=44, fg_color=FIELD, border_color=BORDER, font=(FONT, 13), corner_radius=10)
        self.search_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkOptionMenu(controls, values=["All", "Income", "Expense"], variable=self.filter_type, command=lambda _: self._update_transaction_results(), width=125, height=44, fg_color=PANEL_2, button_color=PANEL_2, button_hover_color=BORDER, corner_radius=10).pack(side="left", padx=(12, 0))
        self.results_host = ctk.CTkFrame(self.content, fg_color="transparent")
        self.results_host.pack(fill="both", expand=True)
        self._update_transaction_results()

    def _on_search(self, *_):
        # Debounce: wait until the user pauses typing instead of
        # re-querying and rebuilding the whole table on every keystroke.
        if self._search_job is not None:
            self.after_cancel(self._search_job)
        self._search_job = self.after(250, self._run_search)

    def _run_search(self):
        self._search_job = None
        if getattr(self, "page", None) == "transactions" and hasattr(self, "results_host") and self.results_host.winfo_exists():
            self._update_transaction_results()

    def _update_transaction_results(self):
        if self.page != "transactions" or not self.results_host.winfo_exists():
            return
        keyword = self.search_var.get().strip().lower()
        kind = self.filter_type.get()
        results = []
        for record in get_transactions():
            _, t_type, category, amount, t_date = record
            if kind != "All" and kind != t_type:
                continue
            searchable = f"{t_type} {category} {amount:.2f} {t_date}".lower()
            if keyword in searchable:
                results.append(record)
        for widget in self.results_host.winfo_children():
            widget.destroy()
        self._render_transactions(self.results_host, results, f"Transaction history  ·  {len(results)} records")

    def _render_transactions(self, parent, records, title, show_all=False):
        panel = ctk.CTkFrame(parent, fg_color=PANEL, border_color=BORDER, border_width=1, corner_radius=16)
        panel.pack(fill="both", expand=True, padx=32, pady=(0, 29))
        heading = ctk.CTkFrame(panel, fg_color="transparent")
        heading.pack(fill="x", padx=20, pady=(19, 10))
        ctk.CTkLabel(heading, text=title, font=(FONT, 18, "bold"), text_color=WHITE).pack(side="left")
        if show_all:
            ctk.CTkButton(heading, text="View all  →", fg_color="transparent", hover_color=PANEL_2, text_color=ACCENT, width=94, command=self.show_transactions).pack(side="right")

        table = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        table.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        for i, weight in enumerate((3, 2, 2, 2, 1)):
            table.grid_columnconfigure(i, weight=weight, uniform="transaction")
        for col, text in enumerate(("CATEGORY", "DATE", "TYPE", "AMOUNT", "")):
            ctk.CTkLabel(table, text=text, anchor="w", font=(FONT, 10, "bold"), text_color=MUTED).grid(row=0, column=col, sticky="ew", padx=10, pady=(8, 14))

        if not records:
            searching = self.page == "transactions" and self.search_var.get().strip()
            message = "No transactions match your search." if searching else "No transactions yet."
            ctk.CTkLabel(table, text=message, font=(FONT, 14, "bold"), text_color=WHITE).grid(row=1, column=0, columnspan=5, pady=(40, 12))
            if not searching:
                ctk.CTkButton(table, text="+  Add your first transaction", command=self.add_dialog, height=38,
                              fg_color=ACCENT, hover_color=ACCENT_HOVER, corner_radius=10).grid(row=2, column=0, columnspan=5, pady=(0, 40))
            return

        for i, (tid, kind, category, amount, when) in enumerate(records, start=1):
            color = GREEN if kind == "Income" else ORANGE
            cells = (category, when, kind, f"{'+' if kind == 'Income' else '−'}{peso(amount)}")
            for j, val in enumerate(cells):
                item = ctk.CTkFrame(table, fg_color=PANEL_2 if i % 2 else PANEL,
                                    corner_radius=8, height=44)
                item.grid(row=i, column=j, sticky="ew", padx=3, pady=3)
                item.grid_propagate(False)
                ctk.CTkLabel(item, text=val, anchor="w", font=(FONT, 12, "bold" if j in (0, 3) else "normal"),
                             text_color=color if j == 3 else (WHITE if j == 0 else MUTED)).pack(side="left", padx=12, fill="x", expand=True)
            ctk.CTkButton(table, text="Delete", width=72, height=34,
                          fg_color=PANEL_2, hover_color="#633545", text_color=RED,
                          corner_radius=10, command=lambda item_id=tid: self.confirm_delete(item_id)).grid(row=i, column=4, padx=5, pady=7)

    # ---------------- FINANCIAL REPORT ----------------

    def show_reports(self):
        self.page = "reports"
        self._clear_content()
        self._activate_nav()
        self._header("Financial report", "Explore where your money goes, month by month.")

        tools = ctk.CTkFrame(self.content, fg_color="transparent")
        tools.pack(fill="x", padx=32, pady=(0, 14))

        ctk.CTkSegmentedButton(
            tools, values=["Monthly", "All time"], variable=self.report_mode,
            selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
            unselected_color=PANEL_2, unselected_hover_color=BORDER,
            height=40, font=(FONT, 12, "bold"),
            command=lambda _: self._refresh_report(),
        ).pack(side="left")

        # Month navigator: ◀ November 2026 ▶  (replaces typing YYYY-MM by hand)
        nav = ctk.CTkFrame(tools, fg_color=PANEL_2, corner_radius=10)
        nav.pack(side="left", padx=(12, 0))
        self.prev_month_btn = ctk.CTkButton(
            nav, text="◀", width=38, height=40, fg_color="transparent",
            hover_color=BORDER, command=lambda: self._change_month(-1))
        self.prev_month_btn.pack(side="left")
        self.month_title = ctk.CTkLabel(nav, text="", width=150, font=(FONT, 13, "bold"))
        self.month_title.pack(side="left")
        self.next_month_btn = ctk.CTkButton(
            nav, text="▶", width=38, height=40, fg_color="transparent",
            hover_color=BORDER, command=lambda: self._change_month(1))
        self.next_month_btn.pack(side="left")

        ctk.CTkButton(
            tools, text="Export CSV  ↗", width=125, height=40,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self.export_report,
        ).pack(side="right")

        self.report_message = ctk.CTkLabel(tools, text="", text_color=GREEN, font=(FONT, 11))
        self.report_message.pack(side="left", padx=(12, 0))

        self.report_host = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        self.report_host.pack(fill="both", expand=True, padx=26, pady=(0, 20))
        self._refresh_report()

    def _change_month(self, delta):
        target = shift_month(self.report_month, delta)
        if target > shift_month(date.today().replace(day=1), 0):
            return  # no future months
        self.report_month = target
        self._refresh_report()

    def _report_records(self, all_records=None):
        """Return (records, period_label) for the selected period."""
        records = get_transactions() if all_records is None else all_records
        if self.report_mode.get() == "All time":
            return records, "All time"
        return records_in_month(records, self.report_month), month_label(self.report_month)

    def _refresh_report(self):
        if self.page != "reports" or not self.report_host.winfo_exists():
            return
        monthly = self.report_mode.get() == "Monthly"
        this_month = date.today().replace(day=1)

        # Month navigator only applies to the Monthly view.
        self.month_title.configure(text=month_label(self.report_month),
                                   text_color=WHITE if monthly else MUTED)
        self.prev_month_btn.configure(state="normal" if monthly else "disabled")
        self.next_month_btn.configure(
            state="normal" if monthly and self.report_month < this_month else "disabled")
        self.report_message.configure(text="")

        all_records = get_transactions()
        records, period = self._report_records(all_records)

        for widget in self.report_host.winfo_children():
            widget.destroy()

        income = sum(float(r[3]) for r in records if r[1] == "Income")
        expense = sum(float(r[3]) for r in records if r[1] == "Expense")
        cards = ctk.CTkFrame(self.report_host, fg_color="transparent")
        cards.pack(fill="x", pady=(2, 20))
        self._card(cards, "Income", income, GREEN, "↗")
        self._card(cards, "Expenses", expense, RED, "↘")
        self._card(cards, "Net cash flow", income - expense, WHITE, "◈")

        chart_end = self.report_month if monthly else this_month
        self._render_chart(self.report_host, monthly_totals(all_records, chart_end, 6),
                           highlight=self.report_month if monthly else None)
        self._render_breakdown(self.report_host, records, period, expense)

    def _render_chart(self, parent, data, highlight=None):
        panel = ctk.CTkFrame(parent, fg_color=PANEL, border_width=1, border_color=BORDER, corner_radius=16)
        panel.pack(fill="x", padx=6, pady=(0, 14))
        header = ctk.CTkFrame(panel, fg_color="transparent")
        header.pack(fill="x", padx=22, pady=(19, 4))
        ctk.CTkLabel(header, text="Income vs expenses", font=(FONT, 18, "bold"), text_color=WHITE).pack(side="left")
        ctk.CTkLabel(header, text="●  Expenses", font=(FONT, 11, "bold"), text_color=ORANGE).pack(side="right")
        ctk.CTkLabel(header, text="●  Income", font=(FONT, 11, "bold"), text_color=GREEN).pack(side="right", padx=(0, 16))

        hint = "Hover over a month to see its totals."
        info = ctk.CTkLabel(panel, text=hint, font=(FONT, 11), text_color=MUTED)
        info.pack(anchor="w", padx=22)

        canvas = tk.Canvas(panel, height=210, bg=PANEL, highlightthickness=0)
        canvas.pack(fill="x", padx=22, pady=(4, 18))

        def show_info(month, inc, exp):
            info.configure(text=f"{month_label(month)}   ·   Income {peso(inc)}   ·   Expenses {peso(exp)}",
                           text_color=WHITE)

        def draw(_event=None):
            canvas.delete("all")
            width, height = canvas.winfo_width(), canvas.winfo_height()
            if width < 60:
                return
            top, bottom, side = 24, 30, 6
            baseline = height - bottom
            plot_h = baseline - top
            peak = max([max(inc, exp) for _, inc, exp in data] + [0])
            slot = (width - 2 * side) / len(data)
            bar_w = min(28, slot * 0.28)

            for i, (month, inc, exp) in enumerate(data):
                tag = f"month{i}"
                x0 = side + slot * i
                cx = x0 + slot / 2
                selected = month == highlight
                # Background of each month column; also catches the mouse hover.
                canvas.create_rectangle(x0 + 4, top - 8, x0 + slot - 4, baseline,
                                        fill=PANEL_2 if selected else PANEL, outline="", tags=tag)
                for value, color, offset in ((inc, GREEN, -1), (exp, ORANGE, 1)):
                    if peak and value > 0:
                        bar_h = max(3, value / peak * plot_h)
                        x = cx + offset * (bar_w / 2 + 2)
                        canvas.create_rectangle(x - bar_w / 2, baseline - bar_h, x + bar_w / 2, baseline,
                                                fill=color, outline="", tags=tag)
                canvas.create_text(cx, baseline + 15, text=month.strftime("%b"),
                                   fill=WHITE if selected else MUTED,
                                   font=(FONT, 10, "bold" if selected else "normal"), tags=tag)
                canvas.tag_bind(tag, "<Enter>", lambda _e, m=month, a=inc, b=exp: show_info(m, a, b))
                canvas.tag_bind(tag, "<Leave>", lambda _e: info.configure(text=hint, text_color=MUTED))

            canvas.create_line(side, baseline, width - side, baseline, fill=BORDER)
            if peak:
                canvas.create_text(side, 4, anchor="nw", text=f"Highest: {peso(peak)}",
                                   fill=MUTED, font=(FONT, 9))
            else:
                canvas.create_text(width / 2, top + plot_h / 2, text="No transactions in these months yet.",
                                   fill=MUTED, font=(FONT, 11))

        canvas.bind("<Configure>", draw)

    def _render_breakdown(self, parent, records, period, expense):
        panel = ctk.CTkFrame(parent, fg_color=PANEL, border_width=1, border_color=BORDER, corner_radius=16)
        panel.pack(fill="both", expand=True, padx=6, pady=(0, 14))
        header = ctk.CTkFrame(panel, fg_color="transparent")
        header.pack(fill="x", padx=22, pady=(19, 10))
        ctk.CTkLabel(header, text="Expense breakdown", font=(FONT, 18, "bold"), text_color=WHITE).pack(side="left")
        ctk.CTkLabel(header, text=f"{len(records)} transactions  ·  {period}", font=(FONT, 11), text_color=MUTED).pack(side="right")

        categories = defaultdict(float)
        for _, kind, category, amount, _ in records:
            if kind == "Expense":
                categories[category] += float(amount)
        categories = sorted(categories.items(), key=lambda row: row[1], reverse=True)

        if not categories:
            empty = ctk.CTkFrame(panel, fg_color="transparent")
            empty.pack(pady=(18, 30))
            ctk.CTkLabel(empty, text="No expenses for this period yet.", font=(FONT, 14, "bold"),
                         text_color=WHITE).pack()
            ctk.CTkLabel(empty, text="Add one, or use ◀ ▶ to look at another month.",
                         font=(FONT, 12), text_color=MUTED).pack(pady=(4, 14))
            ctk.CTkButton(empty, text="+  Add transaction", command=self.add_dialog, height=38,
                          fg_color=ACCENT, hover_color=ACCENT_HOVER, corner_radius=10).pack()
            return

        for name, amount in categories:
            line = ctk.CTkFrame(panel, fg_color="transparent")
            line.pack(fill="x", padx=24, pady=(8, 6))
            ctk.CTkLabel(line, text=name, font=(FONT, 12, "bold"), text_color=WHITE, anchor="w").pack(side="left")
            ctk.CTkLabel(line, text=f"{peso(amount)}  ·  {amount / expense * 100:.1f}%", font=(FONT, 12), text_color=MUTED).pack(side="right")
            progress = ctk.CTkProgressBar(panel, height=9, corner_radius=6, progress_color=ORANGE, fg_color=FIELD)
            progress.pack(fill="x", padx=24, pady=(0, 10))
            progress.set(amount / expense if expense else 0)
        ctk.CTkLabel(panel, text="The report uses your saved transactions. Income and expenses are totalled separately.",
                     font=(FONT, 11), text_color=MUTED).pack(anchor="w", padx=24, pady=(12, 18))

    def export_report(self):
        records, period = self._report_records()
        suggested = "financial_report_" + period.replace(" ", "_") + ".csv"
        filename = filedialog.asksaveasfilename(
            parent=self, title="Export financial report", defaultextension=".csv",
            initialfile=suggested, filetypes=[("CSV files", "*.csv")]
        )
        if not filename:
            return
        try:
            income = sum(float(r[3]) for r in records if r[1] == "Income")
            expenses = sum(float(r[3]) for r in records if r[1] == "Expense")
            with open(filename, "w", encoding="utf-8-sig", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["FlowMoney Financial Report", period])
                writer.writerow(["Total income (PHP)", f"{income:.2f}"])
                writer.writerow(["Total expenses (PHP)", f"{expenses:.2f}"])
                writer.writerow(["Net cash flow (PHP)", f"{income - expenses:.2f}"])
                writer.writerow([])
                writer.writerow(["Date", "Type", "Category", "Amount (PHP)"])
                for _, kind, category, amount, when in records:
                    # Guard against spreadsheet formula injection for user-entered categories.
                    safe_category = "'" + category if category.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else category
                    writer.writerow([when, kind, safe_category, f"{float(amount):.2f}"])
        except OSError as err:
            self.show_error(f"Could not export report: {err}")
            return
        self.report_message.configure(text="CSV exported successfully.", text_color=GREEN)

    # ---------------- Custom dialogs (no default Windows popups) ----------------

    def _dialog_base(self, title, subtitle, width=430, height=400):
        if self.active_dialog is not None and self.active_dialog.winfo_exists():
            self.active_dialog.focus_force()
            return None, None
        modal = ctk.CTkToplevel(self)
        self.active_dialog = modal
        modal.title(title)
        modal.geometry(f"{width}x{height}")
        modal.resizable(False, False)
        modal.configure(fg_color=BG)
        modal.transient(self)
        modal.update_idletasks()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - width) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - height) // 2)
        modal.geometry(f"{width}x{height}+{x}+{y}")

        box = ctk.CTkFrame(modal, fg_color=PANEL, border_width=1, border_color=BORDER, corner_radius=18)
        box.pack(fill="both", expand=True, padx=16, pady=16)
        ctk.CTkLabel(box, text=title, font=(FONT, 23, "bold"), text_color=WHITE).pack(anchor="w", padx=26, pady=(25, 8))
        ctk.CTkLabel(box, text=subtitle, font=(FONT, 12), text_color=MUTED, justify="left", wraplength=width - 90).pack(anchor="w", padx=26, pady=(0, 18))

        def close(event=None):
            try:
                modal.grab_release()
            except tk.TclError:
                pass
            if modal.winfo_exists():
                modal.destroy()
            if self.active_dialog is modal:
                self.active_dialog = None
            return "break"

        modal.protocol("WM_DELETE_WINDOW", close)
        modal.bind("<Escape>", close)
        modal.after(80, lambda: modal.grab_set() if modal.winfo_exists() else None)
        return modal, (box, close)

    def add_dialog(self):
        modal, parts = self._dialog_base("New transaction", "Keep your spending organized, one entry at a time.", 470, 600)
        if modal is None:
            return
        body, close = parts
        form = ctk.CTkFrame(body, fg_color="transparent")
        form.pack(fill="x", padx=26)

        def field_label(text):
            ctk.CTkLabel(form, text=text, font=(FONT, 12, "bold"), text_color=MUTED).pack(anchor="w", pady=(0, 6))

        field_label("TYPE")
        kind = ctk.CTkSegmentedButton(form, values=["Expense", "Income"], selected_color=ACCENT, selected_hover_color=ACCENT_HOVER, unselected_color=FIELD, unselected_hover_color=PANEL_2, height=38)
        kind.pack(fill="x", pady=(0, 16))
        kind.set("Expense")

        field_label("CATEGORY  ·  pick one or type a new one")
        existing = get_categories()
        category = ctk.CTkComboBox(
            form, values=category_choices(existing), fg_color=FIELD, border_color=BORDER,
            button_color=PANEL_2, button_hover_color=BORDER, dropdown_fg_color=PANEL,
            dropdown_hover_color=PANEL_2, height=41)
        category.set("")
        category.pack(fill="x", pady=(0, 16))
        # CTkComboBox is a frame around a text entry; focus the entry so typing works.
        category_input = getattr(category, "_entry", category)

        field_label("AMOUNT (PHP)")
        amount = ctk.CTkEntry(form, placeholder_text="0.00", fg_color=FIELD, border_color=BORDER, height=41)
        amount.pack(fill="x", pady=(0, 16))

        field_label("DATE (YYYY-MM-DD)")
        when = ctk.CTkEntry(form, fg_color=FIELD, border_color=BORDER, height=41)
        when.insert(0, date.today().isoformat())
        when.pack(fill="x", pady=(0, 8))

        error_var = tk.StringVar(value="")
        ctk.CTkLabel(form, textvariable=error_var, text_color=RED, font=(FONT, 11), height=28).pack(anchor="w")

        controls = ctk.CTkFrame(body, fg_color="transparent")
        controls.pack(fill="x", padx=26, pady=(8, 0))

        def save(event=None):
            cat = normalize_category(category.get(), category_choices(existing))
            if not cat:
                error_var.set("Please pick or type a category.")
                category_input.focus_set()
                return "break"
            try:
                value = Decimal(amount.get().strip())
                if not value.is_finite() or value <= 0 or value.as_tuple().exponent < -2 or value > Decimal("999999999999"):
                    raise ValueError
            except (InvalidOperation, ValueError):
                error_var.set("Enter a positive amount with up to 2 decimals.")
                amount.focus_set()
                return "break"
            try:
                t_date = datetime.strptime(when.get().strip(), "%Y-%m-%d").date()
                if t_date > date.today():
                    raise ValueError
            except ValueError:
                error_var.set("Enter a valid date (YYYY-MM-DD), not in the future.")
                when.focus_set()
                return "break"
            try:
                add_transaction(kind.get(), cat, float(value), t_date.isoformat())
            except Exception as err:
                error_var.set(f"Could not save: {err}")
                return "break"
            close()
            self._refresh_current_page()
            return "break"

        ctk.CTkButton(controls, text="Cancel", width=110, height=42, fg_color=PANEL_2, hover_color=BORDER, command=close).pack(side="left")
        ctk.CTkButton(controls, text="Save transaction   ↵", height=42, fg_color=ACCENT, hover_color=ACCENT_HOVER, command=save).pack(side="right", fill="x", expand=True, padx=(12, 0))
        # Only Enter and Escape are keyboard shortcuts.
        modal.bind("<Return>", save)
        modal.after(120, lambda: category_input.focus_set() if modal.winfo_exists() else None)

    def confirm_delete(self, transaction_id):
        modal, parts = self._dialog_base("Delete transaction?", "This entry will be permanently removed.\nThis action cannot be undone.", 450, 270)
        if modal is None:
            return
        body, close = parts
        controls = ctk.CTkFrame(body, fg_color="transparent")
        controls.pack(side="bottom", fill="x", padx=25, pady=(0, 25))

        def do_delete(event=None):
            try:
                delete_transaction(transaction_id)
            except Exception as err:
                close()
                self.show_error(str(err))
                return "break"
            close()
            self._refresh_current_page()
            return "break"

        ctk.CTkButton(controls, text="Cancel", height=42, width=125, fg_color=PANEL_2, hover_color=BORDER, command=close).pack(side="left")
        ctk.CTkButton(controls, text="Delete transaction", height=42, fg_color=ORANGE, hover_color=ORANGE_HOVER, command=do_delete).pack(side="right", fill="x", expand=True, padx=(12, 0))
        modal.bind("<Return>", do_delete)

    def show_error(self, text):
        modal, parts = self._dialog_base("Something went wrong", text, 430, 250)
        if modal is None:
            return
        body, close = parts
        ctk.CTkButton(body, text="OK", command=close, height=40, fg_color=ACCENT, hover_color=ACCENT_HOVER).pack(side="bottom", fill="x", padx=26, pady=24)
        modal.bind("<Return>", close)

    def _refresh_current_page(self):
        if self.page == "transactions":
            self.show_transactions()
        elif self.page == "reports":
            self.show_reports()
        else:
            self.show_dashboard()


if __name__ == "__main__":
    FlowMoney().mainloop()
