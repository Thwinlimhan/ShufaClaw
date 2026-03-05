import os
import csv
import logging
import asyncio
from datetime import datetime
from crypto_agent.storage import database
from crypto_agent.data import prices as price_service

logger = logging.getLogger(__name__)

class BackupService:
    @staticmethod
    async def generate_journal_txt():
        """Creates a human-readable text file of all journal entries."""
        entries = database.get_all_journal_entries()
        filename = f"journal_backup_{datetime.now().strftime('%Y%m%d')}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("📔 SHUFACLAW TRADE JOURNAL BACKUP\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}\n")
            f.write("="*40 + "\n\n")
            
            for e in entries:
                f.write(f"Date: {e['timestamp']}\n")
                f.write(f"Type: {e['entry_type'].upper()}\n")
                f.write(f"Symbol: {e['symbol'] if e['symbol'] else 'N/A'}\n")
                f.write(f"Entry: {e['content']}\n")
                if e['outcome']: f.write(f"Outcome: {e['outcome']}\n")
                if e['tags']: f.write(f"Tags: {e['tags']}\n")
                f.write("—"*30 + "\n\n")
        
        return filename

    @staticmethod
    async def generate_notes_txt():
        """Creates a human-readable text file of all notes."""
        notes = database.get_all_notes(active_only=False)
        filename = f"notes_backup_{datetime.now().strftime('%Y%m%d')}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("📌 SHUFACLAW NOTES BACKUP\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}\n")
            f.write("="*40 + "\n\n")
            
            for n in notes:
                status = "ACTIVE" if n['is_active'] else "DELETED"
                f.write(f"[{status}] Category: {n['category'].upper()}\n")
                if n['symbol']: f.write(f"Symbol: {n['symbol']}\n")
                f.write(f"Content: {n['content']}\n")
                f.write("—"*30 + "\n\n")
        
        return filename

    @staticmethod
    async def generate_portfolio_csv():
        """Creates a CSV file with current portfolio values."""
        positions = database.get_all_positions()
        filename = f"portfolio_history_{datetime.now().strftime('%Y%m%d')}.csv"
        
        headers = ['date', 'symbol', 'quantity', 'avg_buy_price', 'price_at_backup', 'value', 'pnl_pct']
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
            date_str = datetime.now().strftime('%Y-%m-%d')
            for p in positions:
                price, _ = await price_service.get_price(p['symbol'])
                val = p['quantity'] * (price or 0)
                cost = p['quantity'] * p['avg_price']
                pnl_pct = ((val - cost) / cost * 100) if cost > 0 else 0
                
                writer.writerow([
                    date_str, p['symbol'], p['quantity'], p['avg_price'],
                    price or "N/A", val, round(pnl_pct, 2)
                ])
                
        return filename

    @staticmethod
    async def generate_trades_csv():
        """Creates a clean CSV of all trade journal entries for Excel."""
        entries = database.get_all_journal_entries()
        filename = f"trade_export_{datetime.now().strftime('%Y%m%d')}.csv"
        
        headers = ['date', 'type', 'symbol', 'entry', 'outcome', 'tags']
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for e in entries:
                writer.writerow([
                    e['timestamp'], e['entry_type'], e['symbol'] or '',
                    e['content'], e['outcome'] or '', e['tags'] or ''
                ])
        
        return filename

    @classmethod
    async def run_full_backup(cls, bot, chat_id):
        """Orchestrates a full backup and sends files to Telegram."""
        try:
            files = []
            files.append(await cls.generate_journal_txt())
            files.append(await cls.generate_notes_txt())
            files.append(await cls.generate_portfolio_csv())
            
            await bot.send_message(chat_id=chat_id, text="💾 **Starting full data backup...**", parse_mode='Markdown')
            
            for f in files:
                with open(f, 'rb') as doc:
                    await bot.send_document(chat_id=chat_id, document=doc)
                os.remove(f) # Clean up after sending
                
            await bot.send_message(chat_id=chat_id, text="✅ **Backup complete!** All files sent safely.", parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            await bot.send_message(chat_id=chat_id, text="❌ Backup failed. Check system logs.")

    @staticmethod
    def get_trading_stats():
        """Gathers statistics about trading behavior."""
        journal_total = len(database.get_all_journal_entries())
        journal_week = database.get_weekly_journal_count()
        
        # Most journaled symbol
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT symbol, COUNT(*) as count FROM trade_journal WHERE symbol IS NOT NULL GROUP BY symbol ORDER BY count DESC LIMIT 1")
        row = cursor.fetchone()
        most_journaled = f"{row[0]} ({row[1]} times)" if row else "None"
        
        positions = database.get_all_positions()
        oldest_sym, oldest_days = database.get_oldest_position()
        
        active_alerts, triggered_alerts = database.get_alert_stats()
        
        notes = database.get_all_notes(active_only=False)
        active_notes = len([n for n in notes if n['is_active']])
        
        stats = (
            "📈 **YOUR TRADING STATS**\n"
            "─────────────────────\n\n"
            "📔 **JOURNAL:**\n"
            f"Total Entries: **{journal_total}**\n"
            f"This Week: **{journal_week}**\n"
            f"Most Journaled: **{most_journaled}**\n\n"
            "💼 **PORTFOLIO:**\n"
            f"Positions: **{len(positions)} coins**\n"
            f"Oldest Position: **{oldest_sym if oldest_sym else 'N/A'}** ({oldest_days} days ago)\n\n"
            "🔔 **ALERTS:**\n"
            f"Total Set: **{active_alerts + triggered_alerts}**\n"
            f"Triggered: **{triggered_alerts}**\n"
            f"Currently Active: **{active_alerts}**\n\n"
            "📌 **NOTES:**\n"
            f"Total Saved: **{len(notes)}**\n"
            f"Active: **{active_notes}**"
        )
        return stats
