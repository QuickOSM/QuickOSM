"""Query Highlighter class."""

from qgis.PyQt.QtCore import QRegularExpression, Qt
from qgis.PyQt.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat


class QueryHighlighter(QSyntaxHighlighter):
    """Query Highlighter class."""

    def __init__(self, parent=None):
        super().__init__(parent)

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(Qt.GlobalColor.darkMagenta)

        keyword_patterns = [
            "\\?xml\\b", "/>", ">", "<",
            ";", r"\[", r"\]", r"\(", r"\)"
        ]

        self.highlightingRules = [
            (QRegularExpression(pattern), keyword_format)
            for pattern in keyword_patterns
        ]

        element_format = QTextCharFormat()
        element_format.setForeground(QColor("#117700"))
        self.highlightingRules.append(
            (QRegularExpression("\\b[A-Za-z_\\-]+(?=[\\s\\/>:;])"), element_format))

        nominatim_area_format = QTextCharFormat()
        nominatim_area_format.setFontItalic(True)
        nominatim_area_format.setFontWeight(QFont.Weight.Bold)
        nominatim_area_format.setForeground(QColor("#FF7C00"))
        self.highlightingRules.append(
            (QRegularExpression(r"\{\{[A-Za-z0-9:, ]*\}\}"), nominatim_area_format))

        attribute_format = QTextCharFormat()
        attribute_format.setFontItalic(True)
        attribute_format.setForeground(QColor("#2020D2"))
        self.highlightingRules.append(
            (QRegularExpression("\\b[A-Za-z0-9_-]+(?=\\=|\\[|\\(|$|\\.)"), attribute_format))

        value_format = QTextCharFormat()
        value_format.setForeground(Qt.GlobalColor.red)
        self.highlightingRules.append(
            (QRegularExpression("(\"[A-Za-z0-9:, _.]*\"|\\:([0-9]+)(?=\\,|\\]))"), value_format))

        area_format = QTextCharFormat()
        area_format.setForeground(QColor("#11CC00"))
        area_pattern = [
            "\\.([A-Za-z0-9_]{2,})(?=\\)|\\;)",
            r"\(([0-9]{2,})\)", "[0-9]+[.]+[0-9]+"
        ]
        for pattern in area_pattern:
            self.highlightingRules.append(
                (QRegularExpression(pattern), area_format))

        single_line_comment_format = QTextCharFormat()
        single_line_comment_format.setForeground(Qt.GlobalColor.gray)
        self.highlightingRules.append(
            (QRegularExpression("(<!--[^\n]*-->|//[^\n]*)"), single_line_comment_format))

        # Multi lines comment
        self.oql_start_comment = QRegularExpression(r"\/\*")
        self.oql_end_comment = QRegularExpression(r'\*\/')

    def match_multiline(
            self, text: str,
            start_delimiter: QRegularExpression,
            end_delimiter: QRegularExpression,
            in_state: int,
            style: Qt) -> bool:
        """Do highlight of multi-line strings. ``delimiter`` should be a
        ``QRegularExpression`` for triple-single-quotes or triple-double-quotes, and
        ``in_state`` should be a unique integer to represent the corresponding
        state changes when inside those strings. Returns True if we're still
        inside a multi-line string when this function is finished.
        """
        # If inside triple-single quotes, start at 0
        if self.previousBlockState() == in_state:
            start = 0
            add = 0
        # Otherwise, look for the delimiter on this line
        else:
            match = start_delimiter.match(text)
            start = match.capturedStart() if match.hasMatch() else -1
            # Move past this match
            add = match.capturedLength() if match.hasMatch() else 0

        # As long as there's a delimiter match on this line...
        while start >= 0:
            # Look for the ending delimiter
            end_match = end_delimiter.match(text, start + add)
            end = end_match.capturedStart() if end_match.hasMatch() else -1
            # Ending delimiter on this line?
            if end >= add:
                length = end - start + add + end_match.capturedLength()
                self.setCurrentBlockState(0)
            # No; multi-line string
            else:
                self.setCurrentBlockState(in_state)
                length = len(text) - start + add
            # Apply formatting
            self.setFormat(start, length, style)
            # Look for the next match
            next_match = end_delimiter.match(text, start + length)
            start = next_match.capturedStart() if next_match.hasMatch() else -1

        # Return True if still inside a multi-line string, False otherwise
        return self.currentBlockState() == in_state

    def highlightBlock(self, text: str):
        """Highlight of a comment block"""
        # for every pattern
        for pattern, char_format in self.highlightingRules:

            # Create a regular expression from the retrieved pattern
            expression = pattern

            # Check what index that expression occurs at with the ENTIRE text
            match_iterator = expression.globalMatch(text)

            # While there are matches
            while match_iterator.hasNext():
                match = match_iterator.next()
                index = match.capturedStart()
                length = match.capturedLength()
                self.setFormat(index, length, char_format)

        # Do multi-line strings
        self.match_multiline(
            text,
            self.oql_start_comment,
            self.oql_end_comment,
            1,
            Qt.GlobalColor.gray)
