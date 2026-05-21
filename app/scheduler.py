import threading
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_scheduler_running = False
_scheduler_thread = None


def start_scheduler(interval_hours=24, run_immediately=True):
    global _scheduler_running, _scheduler_thread

    if _scheduler_running:
        logger.warning("Планировщик уже запущен")
        return False

    _scheduler_running = True

    def scheduler_worker():
        from app import create_app
        from app.parser_service import run_parser_and_save

        logger.info(f"🕐 Планировщик запущен. Интервал: {interval_hours} часов")

        if run_immediately:
            logger.info("🏁 Запуск первого парсинга...")
            app = create_app()
            with app.app_context():
                try:
                    run_parser_and_save()
                except Exception as e:
                    logger.error(f"Ошибка при парсинге: {e}")


        while _scheduler_running:
            time.sleep(interval_hours * 3600)

            if not _scheduler_running:
                break

            logger.info(f"⏰ Плановый запуск парсинга ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
            app = create_app()
            with app.app_context():
                try:
                    run_parser_and_save()
                except Exception as e:
                    logger.error(f"Ошибка при парсинге: {e}")

        logger.info("🛑 Планировщик остановлен")

    _scheduler_thread = threading.Thread(target=scheduler_worker, daemon=True)
    _scheduler_thread.start()

    return True


def stop_scheduler():
    global _scheduler_running

    if not _scheduler_running:
        logger.warning("Планировщик не запущен")
        return False

    logger.info("Остановка планировщика...")
    _scheduler_running = False
    return True

def is_scheduler_running():
    return _scheduler_running