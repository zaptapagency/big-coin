"""MyCoin Desktop GUI — Using Shared State Server.

This version connects to shared_state.py instead of creating its own Node.
Run shared_state.py FIRST, then this app.
"""

import sys
import time
import traceback
from threading import Thread
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QTextEdit,
    QLabel,
    QPushButton,
    QSpinBox,
    QProgressBar,
    QLineEdit,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QFont

from shared_client import SharedStateClient

# Setup logging
import logging
logging.basicConfig(filename='gui_error.log', level=logging.DEBUG,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Signal emitter for thread-safe GUI updates from mining threads
class MiningWorker(QObject):
    """Emits progress signals during mining."""

    progress = pyqtSignal(int, str, int)  # blocks_mined, block_hash, total_utxo
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, shared_client: SharedStateClient, address: str, num_blocks: int):
        super().__init__()
        self.shared_client = shared_client
        self.address = address
        self.num_blocks = num_blocks
        self.should_stop = False

    def run(self):
        """Mine blocks using shared client."""
        try:
            # Start mining via shared state
            self.shared_client.start_mining(self.num_blocks, self.address)

            # Poll status until done
            while True:
                status = self.shared_client.mining_status()
                blocks_mined = status.get("blocks_mined", 0)
                height = status.get("current_height", 0)

                self.progress.emit(blocks_mined, f"height {height}", 0)

                if not status.get("is_mining", False):
                    break

                time.sleep(0.5)

            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        try:
            super().__init__()
            self.setWindowTitle("MyCoin — Desktop Mining (Shared State)")
            self.setGeometry(100, 100, 900, 700)

            # Connect to shared state server
            logger.info("Connecting to shared_state server...")
            self.shared_client = SharedStateClient("127.0.0.1", 9999)
            # Test connection
            info = self.shared_client.blockchain_info()
            logger.info(f"Connected successfully. Blockchain height: {info.get('height')}")
        except Exception as e:
            logger.error(f"ERROR in MainWindow.__init__: {e}")
            logger.error(traceback.format_exc())
            error_msg = (
                f"Cannot connect to shared_state.py\n\nError: {e}\n\n"
                "Make sure shared_state.py is running first!"
            )
            try:
                QMessageBox.critical(None, "Connection Error", error_msg)
            except Exception:
                print(error_msg)
            sys.exit(1)

        self.miner_address: Optional[str] = None
        self.mining_thread: Optional[Thread] = None
        self.mining_worker: Optional[MiningWorker] = None

        # Create tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Tab 1: Wallet
        self.wallet_tab = QWidget()
        self.tabs.addTab(self.wallet_tab, "Wallet")
        self._setup_wallet_tab()

        # Tab 2: Mining
        self.mining_tab = QWidget()
        self.tabs.addTab(self.mining_tab, "Mining")
        self._setup_mining_tab()

        # Tab 3: Blockchain
        self.blockchain_tab = QWidget()
        self.tabs.addTab(self.blockchain_tab, "Blockchain")
        self._setup_blockchain_tab()

        # Tab 4: Settings
        self.settings_tab = QWidget()
        self.tabs.addTab(self.settings_tab, "Settings")
        self._setup_settings_tab()

    def _setup_wallet_tab(self):
        layout = QVBoxLayout()

        # Address display
        layout.addWidget(QLabel("Your Address:"))
        self.address_label = QLineEdit()
        self.address_label.setReadOnly(True)
        layout.addWidget(self.address_label)

        # Generate key button
        btn_new_key = QPushButton("Generate New Key")
        btn_new_key.clicked.connect(self._on_new_key)
        layout.addWidget(btn_new_key)

        # Balance display
        layout.addWidget(QLabel("Balance:"))
        self.balance_label = QLabel("0 coins (0 cents)")
        self.balance_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(self.balance_label)

        # Check balance button
        btn_balance = QPushButton("Check Balance")
        btn_balance.clicked.connect(self._on_check_balance)
        layout.addWidget(btn_balance)

        layout.addStretch()
        self.wallet_tab.setLayout(layout)

    def _setup_mining_tab(self):
        layout = QVBoxLayout()

        # Blocks spinbox
        layout.addWidget(QLabel("Number of Blocks:"))
        self.blocks_spinbox = QSpinBox()
        self.blocks_spinbox.setValue(1)
        self.blocks_spinbox.setMinimum(1)
        self.blocks_spinbox.setMaximum(1000)
        layout.addWidget(self.blocks_spinbox)

        # Mining address
        layout.addWidget(QLabel("Miner Address:"))
        self.mining_address_input = QLineEdit()
        layout.addWidget(self.mining_address_input)

        # Start mining button
        self.btn_start_mining = QPushButton("Start Mining")
        self.btn_start_mining.clicked.connect(self._on_start_mining)
        layout.addWidget(self.btn_start_mining)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Status label
        self.mining_status_label = QLabel("Ready")
        layout.addWidget(self.mining_status_label)

        # Stop mining button
        self.btn_stop_mining = QPushButton("Stop Mining")
        self.btn_stop_mining.setEnabled(False)
        self.btn_stop_mining.clicked.connect(self._on_stop_mining)
        layout.addWidget(self.btn_stop_mining)

        layout.addStretch()
        self.mining_tab.setLayout(layout)

    def _setup_blockchain_tab(self):
        layout = QVBoxLayout()

        self.blockchain_info = QTextEdit()
        self.blockchain_info.setReadOnly(True)
        layout.addWidget(self.blockchain_info)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self._on_refresh_blockchain)
        layout.addWidget(btn_refresh)

        self.blockchain_tab.setLayout(layout)
        self._on_refresh_blockchain()

    def _setup_settings_tab(self):
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Settings (Read-Only)"))
        layout.addWidget(QLabel("Coinbase Maturity: 0 (via shared server)"))

        self.settings_log = QTextEdit()
        self.settings_log.setReadOnly(True)
        self.settings_log.setText("Connected to Shared State Server\nIP: 127.0.0.1\nPort: 9999")
        layout.addWidget(self.settings_log)

        layout.addStretch()
        self.settings_tab.setLayout(layout)

    def _on_new_key(self):
        try:
            result = self.shared_client.new_key()
            self.miner_address = result["address"]
            self.address_label.setText(self.miner_address)
            self.mining_address_input.setText(self.miner_address)
        except Exception as e:
            self.address_label.setText(f"Error: {e}")

    def _on_check_balance(self):
        try:
            result = self.shared_client.get_balance()
            coins = result["balance_coins"]
            cents = result["balance_cents"]
            self.balance_label.setText(f"{coins} coins ({cents} cents)")
        except Exception as e:
            self.balance_label.setText(f"Error: {e}")

    def _on_start_mining(self):
        if not self.miner_address:
            self.mining_status_label.setText("Error: Generate address first")
            return

        blocks = self.blocks_spinbox.value()
        address = self.mining_address_input.text()

        if not address:
            self.mining_status_label.setText("Error: No address specified")
            return

        # Clean up previous thread if still running
        if self.mining_thread is not None and self.mining_thread.isRunning():
            self.mining_thread.quit()
            self.mining_thread.wait()

        self.btn_start_mining.setEnabled(False)
        self.btn_stop_mining.setEnabled(True)
        self.mining_status_label.setText(f"Mining {blocks} blocks...")

        # Create and run worker in thread
        self.mining_worker = MiningWorker(self.shared_client, address, blocks)
        self.mining_thread = QThread()
        self.mining_worker.moveToThread(self.mining_thread)
        self.mining_thread.started.connect(self.mining_worker.run)
        self.mining_worker.progress.connect(self._on_mining_progress)
        self.mining_worker.finished.connect(self._on_mining_finished)
        self.mining_worker.error.connect(self._on_mining_error)
        self.mining_worker.finished.connect(self.mining_thread.quit)
        self.mining_worker.error.connect(self.mining_thread.quit)
        self.mining_thread.start()

    def _on_mining_progress(self, blocks_mined: int, status: str, utxo: int):
        self.progress_bar.setValue(blocks_mined)
        self.mining_status_label.setText(f"{status} — mined {blocks_mined} blocks")

    def _on_mining_finished(self):
        self.btn_start_mining.setEnabled(True)
        self.btn_stop_mining.setEnabled(False)
        self.mining_status_label.setText("Mining complete!")
        # Wait for thread to finish cleanup
        if self.mining_thread is not None:
            self.mining_thread.wait()
        self._on_check_balance()

    def _on_mining_error(self, error: str):
        self.btn_start_mining.setEnabled(True)
        self.btn_stop_mining.setEnabled(False)
        self.mining_status_label.setText(f"Error: {error}")

    def _on_stop_mining(self):
        try:
            self.shared_client.stop_mining()
            self.mining_status_label.setText("Mining stopped")
            self.btn_stop_mining.setEnabled(False)
            self.btn_start_mining.setEnabled(True)
        except Exception as e:
            self.mining_status_label.setText(f"Error: {e}")

    def _on_refresh_blockchain(self):
        try:
            result = self.shared_client.blockchain_info()
            info = f"""
Blockchain Info:
================
Height: {result['height']}
Tip Hash: {result['tip_hash'][:32]}...
Total Money: {result['total_money_coins']} coins ({result['total_money_cents']} cents)
Transactions: {result['tx_count']}
"""
            self.blockchain_info.setText(info)
        except Exception as e:
            self.blockchain_info.setText(f"Error: {e}")


if __name__ == "__main__":
    try:
        logger.info("Starting MyCoin GUI...")
        app = QApplication(sys.argv)
        logger.info("QApplication created")
        window = MainWindow()
        logger.info("MainWindow created")
        window.show()
        logger.info("Window shown, entering event loop")
        sys.exit(app.exec())
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.error(traceback.format_exc())
        print(f"Fatal error: {e}")
        sys.exit(1)
