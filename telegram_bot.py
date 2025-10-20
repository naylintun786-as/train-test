import logging
import os
import sqlite3
import csv
import io
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
import pytz

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from telegram.helpers import escape_markdown

# 🔐 Bot token: prefer environment variable
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8243952842:AAG-t1I8gK6OtbNT2xMltLWiVnXXj4nSNIs")
ADMIN_IDS = [5052512949]  # Replace with your actual Telegram ID

# Database setup
DB_NAME = "workers.db"
YANGON_TZ = pytz.timezone("Asia/Yangon")

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def md(text: object) -> str:
    """Escape text for Telegram Markdown (legacy)"""
    return escape_markdown(str(text), version=1)


class DatabaseManager:
    def __init__(self, db_name: str):
        self.db_name = db_name
        self.init_database()

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def init_database(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Workers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workers(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                emp_id TEXT UNIQUE NOT NULL,
                telegram_id INTEGER UNIQUE NOT NULL,
                rate REAL DEFAULT 5000.0,
                total_hours REAL DEFAULT 0.0,
                total_salary REAL DEFAULT 0.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Attendance table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                clock_in TEXT,
                clock_out TEXT,
                hours REAL DEFAULT 0.0,
                manual_entry BOOLEAN DEFAULT FALSE,
                description TEXT DEFAULT '',
                FOREIGN KEY (worker_id) REFERENCES workers (id),
                UNIQUE(worker_id, date)
            )
        ''')

        conn.commit()
        conn.close()
        print("✅ Database initialized successfully")

    def register_worker(self, name: str, emp_id: str, telegram_id: int) -> bool:
        """Register a new worker"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            # Use INSERT OR IGNORE then UPDATE to avoid REPLACE deleting row and breaking FKs
            cursor.execute('''
                INSERT OR IGNORE INTO workers (name, emp_id, telegram_id)
                VALUES (?, ?, ?)
            ''', (name, emp_id, telegram_id))
            cursor.execute('''
                UPDATE workers SET name = ?, telegram_id = ? WHERE emp_id = ?
            ''', (name, telegram_id, emp_id))
            conn.commit()
            conn.close()
            print(f"✅ Worker registered: {name} ({emp_id})")
            return True
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return False

    def get_worker_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """Get worker details by Telegram ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM workers WHERE telegram_id = ?', (telegram_id,))
            result = cursor.fetchone()
            conn.close()

            if result:
                return {
                    "id": result[0],
                    "name": result[1],
                    "emp_id": result[2],
                    "telegram_id": result[3],
                    "rate": result[4],
                    "total_hours": result[5] or 0.0,
                    "total_salary": result[6] or 0.0,
                }
            return None
        except Exception as e:
            print(f"❌ Get worker error: {e}")
            return None

    def clock_in(self, worker_id: int) -> bool:
        """Record clock-in for today; return False if already clocked-in"""
        try:
            today = date.today().isoformat()
            current_time = datetime.now(YANGON_TZ).strftime("%H:%M:%S")

            conn = self.get_connection()
            cursor = conn.cursor()

            # Check existing attendance row
            cursor.execute(
                'SELECT id, clock_in, manual_entry FROM attendance WHERE worker_id = ? AND date = ?',
                (worker_id, today),
            )
            row = cursor.fetchone()

            if row:
                att_id, clk_in, is_manual = row[0], row[1], row[2]
                # If manual entry exists for today, do not overwrite
                if is_manual:
                    conn.close()
                    return False
                # If already clocked in, return False
                if clk_in is not None and clk_in not in ("", "MANUAL"):
                    conn.close()
                    return False
                # Otherwise, set clock_in
                cursor.execute(
                    'UPDATE attendance SET clock_in = ? WHERE id = ?',
                    (current_time, att_id),
                )
            else:
                cursor.execute(
                    'INSERT INTO attendance (worker_id, date, clock_in) VALUES (?, ?, ?)',
                    (worker_id, today, current_time),
                )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"❌ Clock-in error: {e}")
            return False

    def clock_out(self, worker_id: int) -> Tuple[bool, float]:
        """Record clock-out for today and calculate hours"""
        try:
            today = date.today().isoformat()
            current_time = datetime.now(YANGON_TZ).strftime("%H:%M:%S")

            conn = self.get_connection()
            cursor = conn.cursor()

            # Get attendance row
            cursor.execute(
                'SELECT id, clock_in, hours, manual_entry FROM attendance WHERE worker_id = ? AND date = ?',
                (worker_id, today),
            )
            result = cursor.fetchone()

            if not result:
                conn.close()
                return False, 0.0

            att_id, clock_in_str, existing_hours, is_manual = result

            # If manual entry or no clock-in yet, cannot clock out
            if is_manual or not clock_in_str or clock_in_str == 'MANUAL':
                conn.close()
                return False, 0.0

            clock_in_time = datetime.strptime(clock_in_str, "%H:%M:%S")
            clock_out_time = datetime.strptime(current_time, "%H:%M:%S")

            # Handle potential cross-midnight by clamping to non-negative
            delta_sec = (clock_out_time - clock_in_time).total_seconds()
            if delta_sec < 0:
                delta_sec = 0
            hours_worked = round(delta_sec / 3600, 2)

            # Update attendance record
            cursor.execute(
                'UPDATE attendance SET clock_out = ?, hours = ? WHERE id = ?',
                (current_time, hours_worked, att_id),
            )

            # Update worker's total hours and salary
            worker = self.get_worker_by_id(worker_id)
            if worker:
                new_total_hours = (worker["total_hours"] or 0.0) + hours_worked
                new_total_salary = new_total_hours * worker["rate"]

                cursor.execute(
                    'UPDATE workers SET total_hours = ?, total_salary = ? WHERE id = ?',
                    (new_total_hours, new_total_salary, worker_id),
                )

            conn.commit()
            conn.close()
            return True, hours_worked

        except Exception as e:
            print(f"❌ Clock-out error: {e}")
            return False, 0.0

    def get_worker_by_id(self, worker_id: int) -> Optional[Dict]:
        """Get worker details by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM workers WHERE id = ?', (worker_id,))
            result = cursor.fetchone()
            conn.close()

            if result:
                return {
                    "id": result[0],
                    "name": result[1],
                    "emp_id": result[2],
                    "telegram_id": result[3],
                    "rate": result[4],
                    "total_hours": result[5] or 0.0,
                    "total_salary": result[6] or 0.0,
                }
            return None
        except Exception as e:
            print(f"❌ Get worker by ID error: {e}")
            return None

    def get_attendance_records(self, worker_id: int, days: int = 30) -> List[Dict]:
        """Get attendance records for a worker"""
        try:
            start_date = (date.today() - timedelta(days=days)).isoformat()

            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT date, clock_in, clock_out, hours, manual_entry, description 
                FROM attendance 
                WHERE worker_id = ? AND date >= ?
                ORDER BY date DESC
            ''', (worker_id, start_date))

            records = []
            for row in cursor.fetchall():
                records.append({
                    "date": row[0],
                    "clock_in": row[1],
                    "clock_out": row[2],
                    "hours": row[3] or 0.0,
                    "manual_entry": row[4],
                    "description": row[5],
                })
            conn.close()
            return records
        except Exception as e:
            print(f"❌ Get attendance records error: {e}")
            return []

    def get_all_workers(self) -> List[Dict]:
        """Get all workers for admin panel"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, emp_id, telegram_id, rate, total_hours, total_salary
                FROM workers ORDER BY name
            ''')

            workers = []
            for row in cursor.fetchall():
                workers.append({
                    "id": row[0],
                    "name": row[1],
                    "emp_id": row[2],
                    "telegram_id": row[3],
                    "rate": row[4],
                    "total_hours": row[5] or 0.0,
                    "total_salary": row[6] or 0.0,
                })
            conn.close()
            return workers
        except Exception as e:
            print(f"❌ Get all workers error: {e}")
            return []

    def get_all_attendance_data(self) -> List[Dict]:
        """Get all attendance data for report generation"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT w.name, w.emp_id, a.date, a.clock_in, a.clock_out, a.hours, a.manual_entry, a.description
                FROM attendance a
                JOIN workers w ON a.worker_id = w.id
                ORDER BY a.date DESC, w.name
            ''')

            data = []
            for row in cursor.fetchall():
                data.append({
                    "name": row[0],
                    "emp_id": row[1],
                    "date": row[2],
                    "clock_in": row[3],
                    "clock_out": row[4],
                    "hours": row[5] or 0.0,
                    "manual_entry": row[6],
                    "description": row[7],
                })
            conn.close()
            return data
        except Exception as e:
            print(f"❌ Get all attendance data error: {e}")
            return []

    def add_manual_hours_worker(self, worker_id: int, target_date: str, hours: float, description: str = "") -> bool:
        """Add manual hours for a worker"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Check if record exists
            cursor.execute('SELECT id, hours FROM attendance WHERE worker_id = ? AND date = ?', (worker_id, target_date))
            result = cursor.fetchone()

            if result:
                # Update existing
                existing_hours = result[1] or 0.0
                new_hours = existing_hours + hours
                cursor.execute('''
                    UPDATE attendance SET hours = ?, manual_entry = TRUE, description = ?
                    WHERE id = ?
                ''', (new_hours, f"Manual: {hours}h - {description}", result[0]))
            else:
                # Create new
                cursor.execute('''
                    INSERT INTO attendance (worker_id, date, clock_in, clock_out, hours, manual_entry, description)
                    VALUES (?, ?, 'MANUAL', 'MANUAL', ?, TRUE, ?)
                ''', (worker_id, target_date, hours, f"Manual: {hours}h - {description}"))

            # Update worker totals
            worker = self.get_worker_by_id(worker_id)
            if worker:
                new_total_hours = (worker["total_hours"] or 0.0) + hours
                new_total_salary = new_total_hours * worker["rate"]
                cursor.execute('UPDATE workers SET total_hours = ?, total_salary = ? WHERE id = ?', 
                             (new_total_hours, new_total_salary, worker_id))

            conn.commit()
            conn.close()
            print(f"✅ Manual hours added: {hours}h for worker {worker_id} on {target_date}")
            return True
        except Exception as e:
            print(f"❌ Add manual hours error: {e}")
            return False

    def update_worker_rate(self, worker_id: int, new_rate: float) -> bool:
        """Update worker's hourly rate"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE workers SET rate = ?, total_salary = total_hours * ? WHERE id = ?', 
                         (new_rate, new_rate, worker_id))
            conn.commit()
            conn.close()
            print(f"✅ Rate updated for worker {worker_id} to {new_rate}")
            return True
        except Exception as e:
            print(f"❌ Update rate error: {e}")
            return False


# Initialize database
db = DatabaseManager(DB_NAME)


def get_main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Create main menu keyboard"""
    keyboard = [
        [InlineKeyboardButton("🕒 Log Working Hours", callback_data="log_hours")],
        [InlineKeyboardButton("💰 Check Salary", callback_data="check_salary")],
        [InlineKeyboardButton("🧾 Register/Update Profile", callback_data="register")],
        [InlineKeyboardButton("📅 View Attendance Record", callback_data="attendance")],
        [InlineKeyboardButton("➕ Add Manual Hours", callback_data="add_manual_hours")],
    ]

    if is_admin:
        keyboard.append([InlineKeyboardButton("📤 Admin Panel", callback_data="admin_panel")])

    return InlineKeyboardMarkup(keyboard)


def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Create admin panel keyboard"""
    keyboard = [
        [InlineKeyboardButton("🧑‍🤝‍🧑 View All Workers", callback_data="admin_view_workers")],
        [InlineKeyboardButton("📊 Generate Report", callback_data="admin_generate_report")],
        [InlineKeyboardButton("💰 Update Salary Rate", callback_data="admin_update_rate")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_log_hours_keyboard() -> InlineKeyboardMarkup:
    """Create clock in/out keyboard"""
    keyboard = [
        [InlineKeyboardButton("⏰ Clock In", callback_data="clock_in")],
        [InlineKeyboardButton("⏹️ Clock Out", callback_data="clock_out")],
        [InlineKeyboardButton("➕ Add Manual Hours", callback_data="add_manual_hours")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_IDS

    welcome_text = (
        "\n".join(
            [
                "👋 Welcome to *Michael Nordic Group Bot*!",
                "",
                "*Worker Features:*",
                "• 🕒 Log working hours (Clock in/out)",
                "• 💰 Check your salary and hours",
                "• 🧾 Register or update your profile",
                "• 📅 View your attendance records",
                "• ➕ Add manual hours (if you forget to clock in/out)",
            ]
        )
    )
    if is_admin:
        welcome_text += "\n\n*Admin Features:*\n• 📤 Access admin panel for reports and management"

    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_menu_keyboard(is_admin),
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        "\n".join(
            [
                "*🤖 Michael Nordic Group Bot - Help*",
                "",
                "*Available Commands:*",
                "/start - Show main menu",
                "/help - Show this help message",
                "/report - Generate attendance report (Admin only)",
                "",
                "*Worker Features:*",
                "• Clock In/Out - Log your working hours",
                "• Salary Check - View your total hours and earnings  ",
                "• Profile Management - Register or update your information",
                "• Attendance Records - View your clock-in/out history",
                "• Manual Hours - Add hours if you forget to clock in/out",
                "",
                "*Manual Hours Format:*",
                "`YYYY-MM-DD | hours | description`",
                "Example: `2024-01-15 | 8.5 | Forgot to clock in`",
                "",
                "*Note:* All times are in Asia/Yangon timezone.",
            ]
        )
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /report command (Admin only)"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Access denied. Admin only.")
        return

    try:
        attendance_data = db.get_all_attendance_data()
        if not attendance_data:
            await update.message.reply_text("❌ No attendance data found.")
            return

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Name", "Employee ID", "Date", "Clock In", "Clock Out", "Hours", "Type", "Description"])

        for record in attendance_data:
            record_type = "Manual" if record["manual_entry"] else "Auto"
            writer.writerow([
                record["name"],
                record["emp_id"],
                record["date"],
                record["clock_in"] or "N/A",
                record["clock_out"] or "N/A",
                record["hours"],
                record_type,
                record["description"] or "",
            ])

        csv_data = output.getvalue().encode("utf-8")
        csv_file = io.BytesIO(csv_data)
        csv_file.name = f"attendance_report_{date.today()}.csv"

        await update.message.reply_document(document=csv_file, caption="📊 Attendance Report")
        print("✅ Report generated successfully")

    except Exception as e:
        print(f"❌ Report error: {e}")
        await update.message.reply_text("❌ Error generating report. Please try again.")


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all callback queries"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data
    is_admin = user_id in ADMIN_IDS

    print(f"🔄 Callback received: {data} from user {user_id}")

    try:
        # Main menu and worker features
        if data == "main_menu":
            await show_main_menu(query, is_admin)
        elif data == "log_hours":
            await show_log_hours_menu(query)
        elif data == "check_salary":
            await show_salary_info(query, user_id)
        elif data == "register":
            await start_registration(query, context, user_id)
        elif data == "attendance":
            await show_attendance_records(query, user_id)
        elif data == "add_manual_hours":
            await start_manual_hours_worker(query, context, user_id)
        elif data == "clock_in":
            await handle_clock_in(query, user_id)
        elif data == "clock_out":
            await handle_clock_out(query, user_id)

        # Admin features
        elif data == "admin_panel":
            if is_admin:
                await show_admin_panel(query)
            else:
                await query.edit_message_text("❌ Access denied.")
        elif data == "admin_view_workers":
            await show_all_workers(query)
        elif data == "admin_generate_report":
            await generate_admin_report(query)
        elif data == "admin_update_rate":
            await start_update_rate(query)
        elif data.startswith("select_worker_"):
            # Begin rate update flow
            try:
                worker_id = int(data.split("_")[-1])
            except Exception:
                await query.edit_message_text(
                    "❌ Invalid selection.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]),
                )
                return

            worker = db.get_worker_by_id(worker_id)
            if not worker:
                await query.edit_message_text(
                    "❌ Worker not found.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]),
                )
                return

            context.user_data["awaiting_rate_update"] = True
            context.user_data["selected_worker_id"] = worker_id

            text = (
                f"💰 *Update Salary Rate*\n\n"
                f"*Worker:* {md(worker['name'])} ({md(worker['emp_id'])})\n"
                f"*Current Rate:* {worker['rate']:,.0f} MMK/hour\n\n"
                f"Send the new hourly rate as a number (e.g., `6000`)."
            )
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="admin_panel")]]),
                parse_mode="Markdown",
            )

    except Exception as e:
        print(f"❌ Callback error: {e}")
        await query.edit_message_text("❌ An error occurred. Please try /start again.")


async def show_main_menu(query, is_admin: bool = False):
    """Show main menu"""
    await query.edit_message_text(
        "🏠 *Main Menu*\n\nSelect an option:",
        reply_markup=get_main_menu_keyboard(is_admin),
        parse_mode="Markdown"
    )


async def show_log_hours_menu(query):
    """Show clock in/out menu"""
    await query.edit_message_text(
        "🕒 *Log Working Hours*\n\nChoose an action:",
        reply_markup=get_log_hours_keyboard(),
        parse_mode="Markdown"
    )


async def show_salary_info(query, user_id: int):
    """Show salary information for worker"""
    worker = db.get_worker_by_telegram_id(user_id)

    if not worker:
        await query.edit_message_text(
            "❌ You need to register first! Use the registration feature.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]])
        )
        return

    text = (
        "\n".join(
            [
                "💰 *Salary Information*",
                "",
                f"*Name:* {md(worker['name'])}",
                f"*Employee ID:* {md(worker['emp_id'])}",
                f"*Hourly Rate:* {worker['rate']:,.0f} MMK",
                f"*Total Hours:* {worker['total_hours']:.2f} hours",
                f"*Total Salary:* {worker['total_salary']:,.0f} MMK",
            ]
        )
    )
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]),
        parse_mode="Markdown"
    )


async def start_registration(query, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Start registration process"""
    worker = db.get_worker_by_telegram_id(user_id)

    if worker:
        text = (
            "\n".join(
                [
                    "🧾 *Update Profile*",
                    "",
                    "Your current information:",
                    f"*Name:* {md(worker['name'])}",
                    f"*Employee ID:* {md(worker['emp_id'])}",
                    "",
                    "Send your updated information:",
                    "`Full Name | Employee ID`",
                    "",
                    "Example: `John Doe | EMP001`",
                ]
            )
        )
    else:
        text = (
            "\n".join(
                [
                    "🧾 *Registration*",
                    "",
                    "Send your information:",
                    "`Full Name | Employee ID`",
                    "",
                    "Example: `John Doe | EMP001`",
                ]
            )
        )

    context.user_data["awaiting_registration"] = True

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="main_menu")]]),
        parse_mode="Markdown",
    )


async def show_attendance_records(query, user_id: int):
    """Show attendance records for worker"""
    worker = db.get_worker_by_telegram_id(user_id)

    if not worker:
        await query.edit_message_text(
            "❌ You need to register first!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]])
        )
        return

    records = db.get_attendance_records(worker["id"], days=30)

    if not records:
        text = "📅 *Attendance Records*\n\nNo records found for the last 30 days."
    else:
        text = "📅 *Attendance Records (Last 30 days)*\n\n"
        text += "*Date       | In     | Out    | Hours*\n"
        text += "--------------------------------\n"

        for record in records[:10]:  # Show only last 10 records
            clock_in = record["clock_in"] or "--:--"
            clock_out = record["clock_out"] or "--:--"
            hours = record["hours"]
            display_date = datetime.strptime(record["date"], "%Y-%m-%d").strftime("%d/%m")

            # Avoid slicing non-time strings like 'MANUAL'
            ci = clock_in[:5] if len(clock_in) >= 5 and clock_in[2] == ":" else clock_in
            co = clock_out[:5] if len(clock_out) >= 5 and clock_out[2] == ":" else clock_out

            text += f"{display_date} | {ci} | {co} | {hours:>5.1f}\n"

        if len(records) > 10:
            text += f"\n... and {len(records) - 10} more records"

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]),
        parse_mode="Markdown"
    )


async def start_manual_hours_worker(query, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Start manual hours process for worker"""
    worker = db.get_worker_by_telegram_id(user_id)

    if not worker:
        await query.edit_message_text(
            "❌ You need to register first!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]])
        )
        return

    text = (
        "\n".join(
            [
                "➕ *Add Manual Working Hours*",
                "",
                "*Use this if you forgot to clock in/out!*",
                "",
                "Send the details:",
                "`YYYY-MM-DD | hours | description`",
                "",
                "*Examples:*",
                "`2024-01-15 | 8.5 | Forgot to clock in today`",
                "`2024-01-14 | 4.0 | Morning shift`",
                "",
                "*Your Information:*",
                f"*Name:* {md(worker['name'])}",
                f"*Employee ID:* {md(worker['emp_id'])}",
                f"*Current Rate:* {worker['rate']:,.0f} MMK/hour",
            ]
        )
    )

    context.user_data["awaiting_manual_hours"] = True

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="main_menu")]]),
        parse_mode="Markdown",
    )


async def handle_clock_in(query, user_id: int):
    """Handle clock in"""
    worker = db.get_worker_by_telegram_id(user_id)

    if not worker:
        await query.edit_message_text(
            "❌ You need to register first!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]])
        )
        return

    success = db.clock_in(worker["id"])
    current_time = datetime.now(YANGON_TZ).strftime("%H:%M:%S")

    if success:
        text = f"✅ *Clocked In Successfully!*\n\nTime: {current_time}\nDate: {date.today().strftime('%d/%m/%Y')}"
    else:
        text = "❌ You have already clocked in today or have a manual entry."

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="log_hours")]]),
        parse_mode="Markdown"
    )


async def handle_clock_out(query, user_id: int):
    """Handle clock out"""
    worker = db.get_worker_by_telegram_id(user_id)

    if not worker:
        await query.edit_message_text(
            "❌ You need to register first!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]])
        )
        return

    success, hours_worked = db.clock_out(worker["id"])
    current_time = datetime.now(YANGON_TZ).strftime("%H:%M:%S")

    if success:
        text = (
            "\n".join(
                [
                    "✅ *Clocked Out Successfully!*",
                    "",
                    f"*Time:* {current_time}",
                    f"*Date:* {date.today().strftime('%d/%m/%Y')}",
                    f"*Hours Worked:* {hours_worked:.2f} hours",
                    f"*Earnings:* {hours_worked * worker['rate']:,.0f} MMK",
                ]
            )
        )
    else:
        text = "❌ You need to clock in first or you have a manual entry."

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="log_hours")]]),
        parse_mode="Markdown"
    )


async def show_admin_panel(query):
    """Show admin panel"""
    await query.edit_message_text(
        "👨‍💼 *Admin Panel*\n\nSelect an option:",
        reply_markup=get_admin_panel_keyboard(),
        parse_mode="Markdown"
    )


async def show_all_workers(query):
    """Show all workers for admin"""
    workers = db.get_all_workers()

    if not workers:
        text = "❌ No workers found."
    else:
        text = "🧑‍🤝‍🧑 *All Workers*\n\n"
        text += "*Name           | Hours  | Salary*\n"
        text += "--------------------------------\n"

        for worker in workers:
            name = worker["name"]
            name_display = name[:12] + "..." if len(name) > 12 else name.ljust(15)
            # Escape markdown in names
            name_display = md(name_display)
            text += f"{name_display} | {worker['total_hours']:>6.1f} | {worker['total_salary']:>8,.0f}\n"

        text += f"\n*Total Workers:* {len(workers)}"

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]),
        parse_mode="Markdown"
    )


async def generate_admin_report(query):
    """Generate and send admin report"""
    try:
        attendance_data = db.get_all_attendance_data()

        if not attendance_data:
            await query.edit_message_text("❌ No attendance data found.")
            return

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Name", "Employee ID", "Date", "Clock In", "Clock Out", "Hours", "Type", "Description"])

        for record in attendance_data:
            record_type = "Manual" if record["manual_entry"] else "Auto"
            writer.writerow([
                record["name"],
                record["emp_id"],
                record["date"],
                record["clock_in"] or "N/A",
                record["clock_out"] or "N/A",
                record["hours"],
                record_type,
                record["description"] or "",
            ])

        csv_data = output.getvalue().encode("utf-8")
        csv_file = io.BytesIO(csv_data)
        csv_file.name = f"attendance_report_{date.today()}.csv"

        await query.message.reply_document(
            document=csv_file, 
            caption="📊 Attendance Report - Generated from Admin Panel"
        )

        await query.edit_message_text(
            "✅ Report generated and sent!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]])
        )

    except Exception as e:
        print(f"❌ Admin report error: {e}")
        await query.edit_message_text(
            "❌ Error generating report.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]])
        )


async def start_update_rate(query):
    """Start the rate update process"""
    workers = db.get_all_workers()

    if not workers:
        await query.edit_message_text("❌ No workers found.")
        return

    keyboard = []
    for worker in workers:
        keyboard.append([
            InlineKeyboardButton(
                f"{worker['name']} ({worker['emp_id']}) - {worker['rate']:,.0f} MMK",
                callback_data=f"select_worker_{worker['id']}"
            )
        ])

    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_panel")])

    await query.edit_message_text(
        "💰 *Update Salary Rate*\n\nSelect a worker:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user_id = update.effective_user.id
    message_text = update.message.text

    print(f"📨 Message received: {message_text} from user {user_id}")

    try:
        # Handle registration
        if context.user_data.get("awaiting_registration"):
            if "|" in message_text:
                parts = [part.strip() for part in message_text.split("|")]
                if len(parts) == 2:
                    name, emp_id = parts
                    success = db.register_worker(name, emp_id, user_id)

                    if success:
                        text = (
                            "\n".join(
                                [
                                    "✅ Successfully registered/updated!",
                                    "",
                                    f"*Name:* {md(name)}",
                                    f"*Employee ID:* {md(emp_id)}",
                                ]
                            )
                        )
                    else:
                        text = "❌ Registration failed. Please try again."

                    context.user_data.pop("awaiting_registration", None)
                    await update.message.reply_text(
                        text,
                        reply_markup=get_main_menu_keyboard(user_id in ADMIN_IDS),
                        parse_mode="Markdown",
                    )
                    return

            await update.message.reply_text(
                "❌ Invalid format. Use: `Full Name | Employee ID`\nExample: `John Doe | EMP001`",
                parse_mode="Markdown",
            )
            return

        # Handle manual hours
        if context.user_data.get("awaiting_manual_hours"):
            if "|" in message_text:
                parts = [part.strip() for part in message_text.split("|")]
                if len(parts) >= 2:
                    try:
                        target_date = parts[0]
                        hours = float(parts[1])
                        description = parts[2] if len(parts) > 2 else "Manual entry"

                        # Validate date
                        datetime.strptime(target_date, "%Y-%m-%d")

                        worker = db.get_worker_by_telegram_id(user_id)
                        if worker:
                            success = db.add_manual_hours_worker(worker["id"], target_date, hours, description)

                            if success:
                                updated_worker = db.get_worker_by_telegram_id(user_id)
                                text = (
                                    "\n".join(
                                        [
                                            "✅ *Manual Hours Added Successfully!*",
                                            "",
                                            f"*Date:* {md(target_date)}",
                                            f"*Hours Added:* {hours:.2f}",
                                            f"*Description:* {md(description)}",
                                            "",
                                            f"*Updated Total Hours:* {updated_worker['total_hours']:.2f}",
                                            f"*Earnings:* {hours * worker['rate']:,.0f} MMK",
                                            f"*Total Salary:* {updated_worker['total_salary']:,.0f} MMK",
                                        ]
                                    )
                                )
                            else:
                                text = "❌ Failed to add manual hours. Please try again."

                            context.user_data.pop("awaiting_manual_hours", None)
                            await update.message.reply_text(
                                text,
                                reply_markup=get_main_menu_keyboard(user_id in ADMIN_IDS),
                                parse_mode="Markdown",
                            )
                            return

                    except ValueError:
                        await update.message.reply_text("❌ Invalid hours format. Use numbers.")
                        return
                    except Exception as e:
                        await update.message.reply_text("❌ Invalid date format. Use YYYY-MM-DD.")
                        return

            await update.message.reply_text(
                "❌ Invalid format. Use: `YYYY-MM-DD | hours | description`\nExample: `2024-01-15 | 8.5 | Forgot to clock in`",
                parse_mode="Markdown",
            )
            return

        # Handle rate updates
        if context.user_data.get("awaiting_rate_update"):
            try:
                new_rate = float(message_text)
                if new_rate <= 0:
                    await update.message.reply_text("❌ Rate must be greater than 0.")
                    return

                worker_id = context.user_data.get("selected_worker_id")
                if worker_id:
                    success = db.update_worker_rate(worker_id, new_rate)

                    if success:
                        worker = db.get_worker_by_id(worker_id)
                        text = (
                            "\n".join(
                                [
                                    "✅ *Rate Updated Successfully!*",
                                    "",
                                    f"*Worker:* {md(worker['name'])}",
                                    f"*New Rate:* {new_rate:,.0f} MMK/hour",
                                    f"*Total Hours:* {worker['total_hours']:.2f} hours",
                                    f"*Total Salary:* {worker['total_salary']:,.0f} MMK",
                                ]
                            )
                        )
                    else:
                        text = "❌ Failed to update rate."

                    context.user_data.pop("awaiting_rate_update", None)
                    context.user_data.pop("selected_worker_id", None)

                    await update.message.reply_text(
                        text,
                        reply_markup=get_admin_panel_keyboard(),
                        parse_mode="Markdown",
                    )
                    return

            except ValueError:
                await update.message.reply_text("❌ Invalid rate. Use numbers like `6000` or `5500`")
            return

    except Exception as e:
        print(f"❌ Message handler error: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")


def main():
    """Start the bot"""
    token = BOT_TOKEN
    if not token or token.strip() == "":
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set. Set env var TELEGRAM_BOT_TOKEN.")

    application = Application.builder().token(token).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("report", report_command))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Michael Nordic Group Bot is running...")
    print("✅ All features are working!")
    print("✅ Database initialized")
    print("✅ Manual hours feature ready")
    print("✅ Report generation ready")

    application.run_polling()


if __name__ == "__main__":
    main()
