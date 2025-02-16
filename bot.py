from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import db
import handlers
import config

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()

def run_health_server():
    """Run health check server"""
    server = HTTPServer(('0.0.0.0', 8080), HealthHandler)
    server.serve_forever()

def main():
    """Main application setup"""
    # Initialize database
    db.init_db()
    
    # Start health server
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # Create bot
    application = ApplicationBuilder().token(config.TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler('start', handlers.start))
    application.add_handler(CommandHandler('add_reminder', handlers.add_reminder))
    application.add_handler(CommandHandler('show_reminders', handlers.show_reminders))
    application.add_handler(CallbackQueryHandler(handlers.mark_done, pattern='^mark_'))
    application.add_handler(CallbackQueryHandler(handlers.show_history, pattern='^history_'))
    
    # Run bot
    application.run_polling()

if __name__ == '__main__':
    main()