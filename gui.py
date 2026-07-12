"""MyCoin Desktop GUI Application using PyQt6.

A user-friendly interface for MyCoin mining and wallet management.
This is an educational project and does not hold real funds.
"""

import sys
import time
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
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QFont

from node import Node
from wallet import Wallet


# Signal emitter for thread-safe GUI updates from mining threads
class MiningWorker(QObject):
    """Emits progress signals during mining."""
    progress = pyqtSignal(int, str, int)  # blocks_mined, block_hash, total_utxo
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, node: Node, miner_address: str, num_blocks: int):
        super().__init__()
        self.node = node
        self.miner_address = miner_address
        self.num_blocks = num_blocks
        self.should_stop = False

    def run(self):
        """Mine `num_blocks` blocks and emit progress."""
        try:
            for i in range(self.num_blocks):
                if self.should_stop:
                    break
                # Mine one block
                block = self.node.mine_block(self.miner_address)
                if block is None:
                    self.error.emit(f"Failed to mine block {i + 1}")
                    break
                # Emit progress
                block_hash = block.hash
                total_utxo = self.node.chain.utxo.total_value()
                self.progress.emit(i + 1, block_hash, total_utxo)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


class WalletTab(QWidget):
    """Tab 1: Wallet management."""

    def __init__(self, node: Node):
        super().__init__()
        self.node = node
        self.wallet = Wallet()
        self.current_address = ""
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Title
        title = QLabel("Wallet Management")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        # Current address section
        layout.addWidget(QLabel("Current Address:"))
        self.address_display = QTextEdit()
        self.address_display.setReadOnly(True)
        self.address_display.setMaximumHeight(60)
        layout.addWidget(self.address_display)

        # Generate new key button
        self.gen_key_btn = QPushButton("Generate New Key")
        self.gen_key_btn.clicked.connect(self.generate_new_key)
        layout.addWidget(self.gen_key_btn)

        # Check balance section
        self.balance_btn = QPushButton("Check Balance")
        self.balance_btn.clicked.connect(self.check_balance)
        layout.addWidget(self.balance_btn)

        self.balance_display = QLabel("Balance: -- coins, -- cents")
        self.balance_display.setFont(QFont("Arial", 11))
        layout.addWidget(self.balance_display)

        # Transaction history
        layout.addWidget(QLabel("Recent Transaction History:"))
        self.tx_history = QTextEdit()
        self.tx_history.setReadOnly(True)
        layout.addWidget(self.tx_history)

        layout.addStretch()
        self.setLayout(layout)

    def generate_new_key(self):
        """Generate a new keypair and display the address."""
        addr = self.wallet.new_key()
        self.current_address = addr
        self.address_display.setText(f"{addr}\n(Base58Check)")
        self.balance_display.setText("Balance: -- coins, -- cents")

    def check_balance(self):
        """Query and display the wallet balance from the UTXO set."""
        if not self.current_address:
            self.balance_display.setText("Balance: No address generated yet")
            return

        utxos = list(self.node.chain.utxo.items())
        balance_cents = self.wallet.balance(utxos)
        coins = balance_cents // 100_000_000
        cents = balance_cents % 100_000_000
        self.balance_display.setText(f"Balance: {coins} coins, {cents} cents")

        # Update transaction history display
        history_text = ""
        for entry in self.wallet.history:
            history_text += (
                f"TxID: {entry['txid'][:16]}...\n"
                f"  To: {entry['to'][:16]}...\n"
                f"  Amount: {entry['amount']} cents\n\n"
            )
        if history_text:
            self.tx_history.setText(history_text)
        else:
            self.tx_history.setText("No transactions yet.")

    def refresh_display(self):
        """Refresh displayed address and balance."""
        if self.current_address:
            self.address_display.setText(f"{self.current_address}\n(Base58Check)")


class MiningTab(QWidget):
    """Tab 2: Mining control."""

    def __init__(self, node: Node, wallet: Wallet):
        super().__init__()
        self.node = node
        self.wallet = wallet
        self.mining_thread: Optional[QThread] = None
        self.mining_worker: Optional[MiningWorker] = None
        self.total_blocks = 1
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Title
        title = QLabel("Mining Control")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        # Number of blocks spinbox
        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel("Number of Blocks:"))
        self.blocks_spinbox = QSpinBox()
        self.blocks_spinbox.setMinimum(1)
        self.blocks_spinbox.setMaximum(1000)
        self.blocks_spinbox.setValue(1)
        hlayout.addWidget(self.blocks_spinbox)
        hlayout.addStretch()
        layout.addLayout(hlayout)

        # Start mining button
        self.start_mining_btn = QPushButton("Start Mining")
        self.start_mining_btn.clicked.connect(self.start_mining)
        layout.addWidget(self.start_mining_btn)

        # Stop mining button (initially disabled)
        self.stop_mining_btn = QPushButton("Stop Mining")
        self.stop_mining_btn.setEnabled(False)
        self.stop_mining_btn.clicked.connect(self.stop_mining)
        layout.addWidget(self.stop_mining_btn)

        # Progress bar
        layout.addWidget(QLabel("Progress:"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("Status: Ready")
        self.status_label.setFont(QFont("Arial", 10))
        layout.addWidget(self.status_label)

        # Info display
        self.info_display = QTextEdit()
        self.info_display.setReadOnly(True)
        layout.addWidget(self.info_display)

        layout.addStretch()
        self.setLayout(layout)

    def start_mining(self):
        """Start mining N blocks in a separate thread."""
        if not self.wallet.addresses:
            self.status_label.setText("Status: Error - No wallet address generated")
            return

        self.total_blocks = self.blocks_spinbox.value()
        miner_address = self.wallet.addresses[-1]

        self.start_mining_btn.setEnabled(False)
        self.stop_mining_btn.setEnabled(True)
        self.blocks_spinbox.setEnabled(False)
        self.progress_bar.setValue(0)

        # Create and start mining worker in a thread
        self.mining_worker = MiningWorker(self.node, miner_address, self.total_blocks)
        self.mining_thread = QThread()
        self.mining_worker.moveToThread(self.mining_thread)

        # Connect signals
        self.mining_thread.started.connect(self.mining_worker.run)
        self.mining_worker.progress.connect(self.on_mining_progress)
        self.mining_worker.finished.connect(self.on_mining_finished)
        self.mining_worker.error.connect(self.on_mining_error)

        self.status_label.setText(f"Status: Mining {self.total_blocks} blocks...")
        self.mining_thread.start()

    def stop_mining(self):
        """Stop the current mining operation."""
        if self.mining_worker:
            self.mining_worker.should_stop = True
        self.status_label.setText("Status: Stopping...")

    def on_mining_progress(self, blocks_mined: int, block_hash: str, total_utxo: int):
        """Update UI with mining progress."""
        progress_pct = (blocks_mined / self.total_blocks) * 100
        self.progress_bar.setValue(int(progress_pct))

        height = self.node.chain.height
        timestamp = self.node.chain.tip_block().header.timestamp
        info = (
            f"Blocks Mined: {blocks_mined} / {self.total_blocks}\n"
            f"Current Height: {height}\n"
            f"Latest Hash: {block_hash[:16]}...\n"
            f"Total UTXO: {total_utxo} cents\n"
            f"Timestamp: {timestamp}"
        )
        self.info_display.setText(info)
        self.status_label.setText(f"Status: Mined {blocks_mined} blocks...")

    def on_mining_finished(self):
        """Handle mining completion."""
        self.progress_bar.setValue(100)
        self.status_label.setText("Status: Mining completed")
        self.start_mining_btn.setEnabled(True)
        self.stop_mining_btn.setEnabled(False)
        self.blocks_spinbox.setEnabled(True)

        if self.mining_thread:
            self.mining_thread.quit()
            self.mining_thread.wait()

    def on_mining_error(self, error_msg: str):
        """Handle mining errors."""
        self.status_label.setText(f"Status: Error - {error_msg}")
        self.start_mining_btn.setEnabled(True)
        self.stop_mining_btn.setEnabled(False)
        self.blocks_spinbox.setEnabled(True)

        if self.mining_thread:
            self.mining_thread.quit()
            self.mining_thread.wait()


class BlockchainTab(QWidget):
    """Tab 3: Blockchain information."""

    def __init__(self, node: Node):
        super().__init__()
        self.node = node
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Title
        title = QLabel("Blockchain Information")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        # Info display
        self.info_display = QTextEdit()
        self.info_display.setReadOnly(True)
        layout.addWidget(self.info_display)

        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_info)
        layout.addWidget(self.refresh_btn)

        layout.addStretch()
        self.setLayout(layout)

        # Initial refresh
        self.refresh_info()

    def refresh_info(self):
        """Fetch and display blockchain info."""
        genesis_hash = self.node.chain.genesis_hash
        tip_hash = self.node.chain.tip
        height = self.node.chain.height
        total_utxo = self.node.chain.utxo.total_value()
        num_blocks = len(self.node.chain.blocks)
        num_transactions = sum(
            len(self.node.chain.blocks[h].transactions)
            for h in self.node.chain.blocks
        )

        info_text = (
            f"Genesis Hash:\n  {genesis_hash}\n\n"
            f"Current Tip Hash:\n  {tip_hash}\n\n"
            f"Chain Height: {height}\n"
            f"Total UTXO Value: {total_utxo} cents\n"
            f"Number of Blocks: {num_blocks}\n"
            f"Number of Transactions: {num_transactions}"
        )
        self.info_display.setText(info_text)


class SettingsTab(QWidget):
    """Tab 4: Application settings."""

    def __init__(self, node: Node):
        super().__init__()
        self.node = node
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Title
        title = QLabel("Settings")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        # Coinbase maturity setting
        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel("Coinbase Maturity (blocks):"))
        self.maturity_spinbox = QSpinBox()
        self.maturity_spinbox.setMinimum(1)
        self.maturity_spinbox.setMaximum(1000)
        self.maturity_spinbox.setValue(self.node.chain.coinbase_maturity)
        hlayout.addWidget(self.maturity_spinbox)
        hlayout.addStretch()
        layout.addLayout(hlayout)

        # Save settings button
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.clicked.connect(self.save_settings)
        layout.addWidget(self.save_btn)

        # Status
        self.status_label = QLabel("Settings saved")
        self.status_label.setFont(QFont("Arial", 10))
        layout.addWidget(self.status_label)

        # Debug/logs area
        layout.addWidget(QLabel("Debug Logs:"))
        self.logs_display = QTextEdit()
        self.logs_display.setReadOnly(True)
        layout.addWidget(self.logs_display)

        layout.addStretch()
        self.setLayout(layout)

        self.log_message(f"Coinbase maturity: {self.node.chain.coinbase_maturity}")
        self.log_message(f"Node ID: {self.node.node_id}")

    def save_settings(self):
        """Save settings (note: maturity affects future blocks, not retroactively)."""
        new_maturity = self.maturity_spinbox.value()
        self.node.chain.coinbase_maturity = new_maturity
        self.status_label.setText(f"Settings saved (maturity={new_maturity})")
        self.log_message(f"Coinbase maturity updated to {new_maturity}")

    def log_message(self, msg: str):
        """Append a message to the logs display."""
        current = self.logs_display.toPlainText()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.logs_display.setText(f"{current}{timestamp}: {msg}\n")


class MainWindow(QMainWindow):
    """Main application window with tabbed interface."""

    def __init__(self, node: Node):
        super().__init__()
        self.node = node
        self.wallet_tab = None
        self.mining_tab = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("MyCoin Mining & Wallet Manager")
        self.setGeometry(100, 100, 900, 700)

        # Central widget with tabs
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)

        # Create wallet (shared between tabs)
        wallet = Wallet()

        # Create tabs
        tabs = QTabWidget()

        # Tab 1: Wallet
        self.wallet_tab = WalletTab(self.node)
        self.wallet_tab.wallet = wallet
        tabs.addTab(self.wallet_tab, "Wallet")

        # Tab 2: Mining
        self.mining_tab = MiningTab(self.node, wallet)
        tabs.addTab(self.mining_tab, "Mining")

        # Tab 3: Blockchain
        blockchain_tab = BlockchainTab(self.node)
        tabs.addTab(blockchain_tab, "Blockchain")

        # Tab 4: Settings
        settings_tab = SettingsTab(self.node)
        tabs.addTab(settings_tab, "Settings")

        layout.addWidget(tabs)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Menu bar
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        # Help menu
        help_menu = menubar.addMenu("Help")
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.show_about)

    def show_about(self):
        """Display about dialog."""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "About MyCoin GUI",
            "MyCoin Mining & Wallet Manager\n\n"
            "An educational desktop application for mining and managing MyCoin.\n"
            "This application does not hold real funds.\n\n"
            "Built with PyQt6",
        )


def main():
    """Main entry point."""
    # Create Node instance
    node = Node("gui-app", coinbase_maturity=100)

    # Create QApplication
    app = QApplication(sys.argv)

    # Create and show main window
    window = MainWindow(node)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
