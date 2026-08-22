import os
import sys
import unittest
from decimal import Decimal

# Set offscreen platform for headless test
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

app = QApplication.instance() or QApplication(sys.argv)


class TestUIPartTimerShifts(unittest.TestCase):

    def setUp(self):
        self.window = MainWindow()

    def tearDown(self):
        if hasattr(self.window, "update_checker") and self.window.update_checker.isRunning():
            self.window.update_checker.quit()
            self.window.update_checker.wait(1000)
        self.window.close()

    def test_part_timer_mode_initial_state(self):
        # Initial full timer mode
        self.assertFalse(self.window.chk_part_timer.isChecked())
        self.assertTrue(self.window.pt_shifts_container.isHidden())

        # Toggle to part timer mode
        self.window.chk_part_timer.setChecked(True)
        self.assertFalse(self.window.pt_shifts_container.isHidden())
        self.assertEqual(len(self.window.shift_rows), 1)

        # Remove button should be disabled for the only remaining row
        self.assertFalse(self.window.shift_rows[0]["btn_remove"].isEnabled())

        # Initial row has + and - buttons
        first_row = self.window.shift_rows[0]
        self.assertEqual(first_row["btn_add"].text(), "+")
        self.assertEqual(first_row["btn_remove"].text(), "-")
        self.assertFalse(first_row["btn_remove"].isEnabled())

        # Click + button on first row to add new row
        first_row["btn_add"].click()
        self.assertEqual(len(self.window.shift_rows), 2)
        self.assertTrue(self.window.shift_rows[0]["btn_remove"].isEnabled())
        self.assertTrue(self.window.shift_rows[1]["btn_remove"].isEnabled())

        # Add 3rd shift row via helper
        self.window.add_shift_row("4.0", "3.0")
        self.assertEqual(len(self.window.shift_rows), 3)

        # Remove middle row
        middle_row = self.window.shift_rows[1]
        self.window.remove_shift_row(middle_row)
        self.assertEqual(len(self.window.shift_rows), 2)

        # Remove last row via helper
        self.window.remove_last_shift_row()
        self.assertEqual(len(self.window.shift_rows), 1)

        # Attempt to remove final row should be prevented
        self.window.remove_last_shift_row()
        self.assertEqual(len(self.window.shift_rows), 1)
        self.assertFalse(self.window.shift_rows[0]["btn_remove"].isEnabled())

    def test_keyboard_shortcuts_in_part_timer_mode(self):
        self.window.chk_part_timer.setChecked(True)
        self.assertEqual(len(self.window.shift_rows), 1)

        # Key '+' (Plus)
        event_plus = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Plus, Qt.KeyboardModifier.NoModifier, "+")
        self.window.keyPressEvent(event_plus)
        self.assertEqual(len(self.window.shift_rows), 2)

        # Key '-' (Minus)
        event_minus = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Minus, Qt.KeyboardModifier.NoModifier, "-")
        self.window.keyPressEvent(event_minus)
        self.assertEqual(len(self.window.shift_rows), 1)

        # Minus on single row does not reduce below 1
        self.window.keyPressEvent(event_minus)
        self.assertEqual(len(self.window.shift_rows), 1)

    def test_keyboard_shortcuts_ignored_in_full_timer_mode(self):
        self.window.chk_part_timer.setChecked(False)
        init_rows = len(self.window.shift_rows)

        event_plus = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Plus, Qt.KeyboardModifier.NoModifier, "+")
        self.window.keyPressEvent(event_plus)
        self.assertEqual(len(self.window.shift_rows), init_rows)

    def test_calculation_and_breakdown_update(self):
        self.window.chk_part_timer.setChecked(True)
        # Configure row 1: 5 days x 8 hrs
        self.window.shift_rows[0]["txt_days"].setText("5.0")
        self.window.shift_rows[0]["txt_hours"].setText("8.0")

        # Add row 2: 3 days x 4 hrs
        self.window.add_shift_row("3.0", "4.0")

        # Set rate and additional
        self.window.txt_pt_rate.setText("15.00")
        self.window.txt_pt_additional.setText("50.00")

        self.window.on_calculate()

        res = self.window.latest_results
        self.assertTrue(res["is_part_timer"])
        self.assertEqual(res["inputs"]["total_working_hours"], 52.0)
        self.assertEqual(res["additions"]["base_wages"], 780.0)
        self.assertEqual(res["nett_salary"], 830.0)

        self.assertIn("52.00 hrs", self.window.lbl_total_hours_summary.text())
        self.assertEqual(self.window.lbl_nett_val.text(), "RM 830.00")


if __name__ == "__main__":
    unittest.main()
