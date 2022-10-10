__COMPILE__ = False


def _compile_input(text):
    if text:
        # escape backslashes and quotes
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        return b'"' + escaped.encode() + b'"?'
    return b"?"


def number_input(text: str = "") -> float|bytes:
    """
    Read user input as a number.

    **Python Equivalent:** ``float(input(...))``

    **Casio Equivalent:** ``?``

    :param text: string to print before the question
    :return: number entered
    """
    if __COMPILE__:
        return _compile_input(text)
    while True:
        try:
            return float(input(f"{text}?\n"))
        except ValueError:
            print("Syntax Error")


def string_input(text: str = "") -> str|bytes:
    """
    Read user input as a string.

    **Python Equivalent:** ``input(...)``

    **Casio Equivalent:** ``?``

    :param text: string to print before the question
    :return: string entered
    """
    if __COMPILE__:
        return _compile_input(text)
    return input(f"{text}?\n")
