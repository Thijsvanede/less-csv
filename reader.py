import argparse
import curses
import numpy as np
import os

class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

class Reader(object):

    def __init__(self, linesep='\n', columnsep=',', escape='\\'):
        # Set separators
        self.linesep   ='\n'
        self.columnsep =','
        self.escape    ='\\'

    def read(self, file):
        """Open csv file and read it.

            Parameters
            ----------
            file : string
                Name of file to read.
            """
        # Set row/column offsets
        self.offset_row    = 1
        self.offset_column = 0

        # Open file
        with open(file) as file:
            # Collect header
            self.columns = self.header(file)

            # Loop forever
            while True:
                # Display data
                self.display(file)
                # Handle user input
                file = self.handle_input(file)

    ########################################################################
    #                           Handle key input                           #
    ########################################################################

    def handle_input(self, file):
        """Handle input from user."""
        # Wait for key input
        key = self.read_single_keypress()

        # Quit on ctrl+C or ctrl+D, q or ESC
        if key == ('\x03',) or key == ('\x04',) or key == ('q',) or\
           key == ('\x1b',):
            # Clear terminal
            self.clear_terminal()
            exit()
        # On up press
        elif key == ('\x1b', '[', 'A'):
            self.offset_row -= 1
        # On down press
        elif key == ('\x1b', '[', 'B'):
            self.offset_row += 1
        # On right press
        elif key == ('\x1b', '[', 'C'):
            self.offset_column = min(self.max_column, self.offset_column + 1)
        # On left press
        elif key == ('\x1b', '[', 'D'):
            self.offset_column = max(0, self.offset_column - 1)
        # On page up press
        elif key == ('\x1b', '[', '5', '~'):
            _, rows = self.terminal_size()
            self.offset_row -= rows - 2
        # On page down press
        elif key == ('\x1b', '[', '6', '~'):
            _, rows = self.terminal_size()
            self.offset_row += rows - 2
        # On home press
        elif key == ('\x1b', '[', 'H'):
            file.seek(0, 0)
        # On end press
        elif key == ('\x1b', '[', 'F'):
            # Get number of rows
            _, rows = self.terminal_size()
            # Go to end of file
            file.seek(0, 2)
            # set row offset
            self.offset_row = - (rows-2)

        # Return file
        return file


    ########################################################################
    #                           Display methods                            #
    ########################################################################

    def display(self, file):
        """Display data to terminal.

            Parameters
            ----------
            file : file
                File to display.
            """
        # Get number of columns and rows to display
        columns, rows = self.terminal_size()
        # Skip offset rows
        file = self.line_move(file, self.offset_row)
        # Get current position of file
        position = file.tell()

        # Erase previous data
        self.clear_terminal()
        # Display partial file contents
        self.data_partial(file, rows, columns)

        # Reset offset row
        self.offset_row = 0
        # Reset file
        file.seek(position, 0)

    # TODO cleanup!!
    def data_partial(self, file, rows, columns):
        """Display given amount of rows and columns from csv file.

            Returns
            -------
            max_column : int
                Maximum column offset.
            """
        # Store data
        data = list()

        # Read appropriate number of lines
        for i, line in enumerate(file):
            # Check if we should break
            if len(data) >= rows - 2: break
            # Append line
            data.append(line.split(self.columnsep))

        # Get data in matrix format
        data = np.asarray(data, dtype=str)

        # Set maximum column offset
        self.max_column = data.shape[1] - 1

        # Compute column widths
        width = np.zeros(data.shape[1], dtype=int)
        for column in range(data.shape[1]):
            width[column] = max(max([len(x) for x in data[:,column]]),
                                len(self.columns[column]))

        # Compute number of rows to show
        nrows = 1
        while self.offset_column + nrows <= data.shape[1] and\
            width[self.offset_column:self.offset_column+nrows].sum() + 3 * nrows < columns:
            nrows += 1
        nrows -= 1

        # Display header
        print(self.header_partial(self.offset_column, self.offset_column + nrows, width))

        # Display data
        # Loop over each row
        for row in data:
            # Initialise line
            line = list()
            # Loop over each cell in columns to display
            for i, cell in enumerate(row[self.offset_column:self.offset_column+nrows]):
                # Add cell with corresponding width
                line.append("{:>{width}}".format(cell.strip(), width=width[self.offset_column+i]))
            # Print line separated by |
            print(' | '.join(line))

    def header(self, file):
        """Read header of file.

            Parameters
            ----------
            file : file
                File from which to read the header.

            Returns
            -------
            header : np.array of shape=(n_columns,)
                Header row
            """
        # Read current position in file
        position = file.tell()

        # Get first line
        for line in file:
            # Read each field as header
            header = line.strip().split(self.columnsep)
            break

        # Reset position of file
        file.seek(position, 0)

        # Return header
        return np.asarray(header)


    def header_partial(self, start, stop, widths):
        """Return partial header of CSV file.

            Requires
            --------
            self.columns is set using self.header()

            Parameters
            ----------
            start : int
                Start index of headers to display

            stop : int
                Stop index of headers to display

            widths : np.array of shape=(n_columns,)
                Width of columns.

            Returns
            -------
            header : string
                String representation of header row
            """
        # Initialise header
        header = list()
        # Add each header field
        for i in range(start, stop):
            header.append(color.BOLD +
                          "{:>{width}}".format(self.columns[i], width=widths[i])
                        + color.END)
        # Return header
        return ' | '.join(header)


    def clear_terminal(self, rows=-1):
        """Clear terminal from previous data."""
        # Get number of rows to clear
        if rows <= 0:
            # Get number of rows to clear
            _, rows = self.terminal_size()

        # Clear those rows
        for row in range(rows):
            print('\x1b[2K', end='\x1b[1A')

    ########################################################################
    #                         File seeking methods                         #
    ########################################################################

    def line_move(self, file, amount=1):
        """Move specified amount of lines in file.

            Parameters
            ----------
            file : file
                File in which to manouvre

            amount : int, default=1
                Amount of lines to move up or down (if negative).

            Returns
            -------
            file : file
                File after moving through file.
            """
        # Move down in case amount is positive
        if amount > 0:
            return self.line_down(file, amount)
        # Move up otherwise
        else:
            return self.line_up(file, abs(amount))

    def line_up(self, file, amount=1):
        """Go up a line in given file.

            Parameters
            ----------
            file : file
                File in which to manouvre

            amount : int, default=1
                Amount of lines to move up.

            Returns
            -------
            file : file
                File after going up a line."""
        # Get current position
        position = file.tell()
        # Get current lookback
        lookback = 1

        # Look back bytes
        while position - lookback > 0 and amount >= 0:
            # Go to previous position
            file.seek(position - lookback, 0)
            # Check if character at that position is linesep
            if file.read(1) == self.linesep:
                # Decrease amount left
                amount -= 1
            # Increment lookback
            lookback += 1

        # Set file to just after on that line
        file.seek(position - lookback + 2, 0)

        # Edge case for first line
        if file.tell() <= 2:
            file.seek(0, 0)
            file = self.line_down(file, 1)

        # Return file
        return file

    def line_down(self, file, amount=1):
        """Go down a line in given file.

            Parameters
            ----------
            file : file
                File in which to manouvre

            amount : int, default=1
                Amount of lines to move down.

            Returns
            -------
            file : file
                File after going down a line."""
        # Go to next line(s)
        for _ in range(amount): file.readline()
        # Make sure there is always a next line
        line = file.readline()
        file = self.line_up(file, 1)
        # Return file
        return file


    ########################################################################
    #                           OS I/O methods                             #
    ########################################################################

    def terminal_size(self):
        """Read terminal size.

            Returns
            -------
            columns : int
                Number of columns to display

            rows : int
                Number of rows to display
            """
        return os.get_terminal_size(0)

    def read_single_keypress(self):
        """Waits for a single keypress on stdin.

        This is a silly function to call if you need to do it a lot because it
        has to store stdin's current setup, setup stdin for reading single
        keystrokes then read the single keystroke then revert stdin back after
        reading the keystroke.

        Returns a tuple of characters of the key that was pressed - on Linux,
        pressing keys like up arrow results in a sequence of characters. Returns
        ('\x03',) on KeyboardInterrupt which can happen when a signal gets
        handled.

        """
        import termios, fcntl, sys, os
        fd = sys.stdin.fileno()
        # save old state
        flags_save = fcntl.fcntl(fd, fcntl.F_GETFL)
        attrs_save = termios.tcgetattr(fd)
        # make raw - the way to do this comes from the termios(3) man page.
        attrs = list(attrs_save) # copy the stored version to update
        # iflag
        attrs[0] &= ~(termios.IGNBRK | termios.BRKINT | termios.PARMRK
                      | termios.ISTRIP | termios.INLCR | termios. IGNCR
                      | termios.ICRNL | termios.IXON )
        # oflag
        attrs[1] &= ~termios.OPOST
        # cflag
        attrs[2] &= ~(termios.CSIZE | termios. PARENB)
        attrs[2] |= termios.CS8
        # lflag
        attrs[3] &= ~(termios.ECHONL | termios.ECHO | termios.ICANON
                      | termios.ISIG | termios.IEXTEN)
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
        # turn off non-blocking
        fcntl.fcntl(fd, fcntl.F_SETFL, flags_save & ~os.O_NONBLOCK)
        # read a single keystroke
        ret = []
        try:
            ret.append(sys.stdin.read(1)) # returns a single character
            fcntl.fcntl(fd, fcntl.F_SETFL, flags_save | os.O_NONBLOCK)
            c = sys.stdin.read(1) # returns a single character
            while len(c) > 0:
                ret.append(c)
                c = sys.stdin.read(1)
        except KeyboardInterrupt:
            ret.append('\x03')
        finally:
            # restore old state
            termios.tcsetattr(fd, termios.TCSAFLUSH, attrs_save)
            fcntl.fcntl(fd, fcntl.F_SETFL, flags_save)
        return tuple(ret)


if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser("CSV file reader")
    parser.add_argument("file", help="CSV file to read.")
    args = parser.parse_args()

    # Create reader
    reader = Reader()
    # Read file
    reader.read(args.file)
