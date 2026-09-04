import os
import sys
import unittest

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QBoxLayout, QFormLayout

from ui.main_window import MainWindow

app = QApplication.instance() or QApplication(sys.argv)


class TestResponsiveLayout(unittest.TestCase):

    def setUp(self):
        self.window = MainWindow()

    def tearDown(self):
        if hasattr(self.window, "update_checker") and self.window.update_checker.isRunning():
            self.window.update_checker.quit()
            self.window.update_checker.wait(1000)
        self.window.close()

    def test_desktop_breakpoint_layout(self):
        """At 1200px+ and 768px, layout should be 2-column side-by-side with right-aligned labels."""
        for width in (768, 1200, 1300):
            self.window.resize(width, 880)
            self.window.update_responsive_layout(width)
            app.processEvents()

            self.assertEqual(self.window.main_layout.direction(), QBoxLayout.Direction.LeftToRight)
            self.assertEqual(self.window.header_layout.direction(), QBoxLayout.Direction.LeftToRight)
            self.assertEqual(self.window.input_form.rowWrapPolicy(), QFormLayout.RowWrapPolicy.DontWrapRows)
            self.assertEqual(self.window.input_form.labelAlignment(), Qt.AlignmentFlag.AlignRight)
            self.assertEqual(self.window.family_socso_layout.direction(), QBoxLayout.Direction.LeftToRight)
            self.assertEqual(self.window.family_layout.rowWrapPolicy(), QFormLayout.RowWrapPolicy.DontWrapRows)

    def test_narrow_breakpoint_stacked_layout(self):
        """Below 768px (e.g. 767px, 600px, 360px), layout should stack to a single column."""
        for width in (360, 600, 767):
            self.window.resize(width, 700)
            self.window.update_responsive_layout(width)
            app.processEvents()

            self.assertEqual(self.window.main_layout.direction(), QBoxLayout.Direction.TopToBottom)
            self.assertEqual(self.window.header_layout.direction(), QBoxLayout.Direction.TopToBottom)
            self.assertEqual(self.window.input_form.rowWrapPolicy(), QFormLayout.RowWrapPolicy.WrapAllRows)
            self.assertEqual(self.window.input_form.labelAlignment(), Qt.AlignmentFlag.AlignLeft)
            self.assertEqual(self.window.family_socso_layout.direction(), QBoxLayout.Direction.TopToBottom)
            self.assertEqual(self.window.family_layout.rowWrapPolicy(), QFormLayout.RowWrapPolicy.WrapAllRows)
            self.assertEqual(self.window.family_layout.labelAlignment(), Qt.AlignmentFlag.AlignLeft)

    def test_fluid_inputs_no_fixed_widths(self):
        """Inputs should resize fluidly without rigid fixed pixel constraints."""
        # Period inputs should have maximumWidth as unbounded (default 16777215)
        self.assertGreater(self.window.txt_month.maximumWidth(), 100)
        self.assertGreater(self.window.txt_year.maximumWidth(), 100)

        # Shift row inputs should have expanding size policy
        self.window.chk_part_timer.setChecked(True)
        shift_row = self.window.shift_rows[0]
        self.assertGreater(shift_row["txt_hours"].maximumWidth(), 100)
        self.assertGreater(shift_row["txt_days"].maximumWidth(), 100)

    def test_word_wrap_radio_and_checkbox(self):
        """WordWrapRadioButton and WordWrapCheckBox should have wordWrap enabled and support click delegation."""
        rb = self.window.radio_socso_cat1
        self.assertTrue(rb.label.wordWrap())
        self.assertTrue(rb.label.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents))
        self.assertTrue(rb.hasHeightForWidth())
        self.assertGreater(rb.heightForWidth(120), rb.heightForWidth(400))

        chk = self.window.chk_socso_injury
        self.assertTrue(chk.label.wordWrap())
        self.assertTrue(chk.label.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents))

        # Check interaction: clicking toggles radio
        self.window.radio_socso_cat2.setChecked(True)
        self.assertTrue(self.window.radio_socso_cat2.isChecked())
        self.assertFalse(self.window.radio_socso_cat1.isChecked())
        self.window.radio_socso_cat1.click()
        self.assertTrue(self.window.radio_socso_cat1.isChecked())


if __name__ == "__main__":
    unittest.main()
