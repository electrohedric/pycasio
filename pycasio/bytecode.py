DISP =          b"\x0c"  # ◢
CARRIAGE =      b"\x0d"  # ↵
ASSIGN =        b"\x0e"  # ➔
EXP =           b"\x0f"  # ᴇ

LT_EQUAL =      b"\x10"  # ≤
NOT_EQUAL =     b"\x11"  # ≠
GT_EQUAL =      b"\x12"  # ≥
IMPLICATION =   b"\x13"  # ⇒

MOD =           b"\x7f\x3a"  # MOD(

MATRIX =        b"\x7f\x40"  # Mat

IMAG =          b"\x7f\x50"  # 𝒊
LIST =          b"\x7f\x51"  # List

ANGLE =         b"\x7f\x54"  # ∠

GETKEY =        b"\x7f\x8f"  # Getkey

AND =           b"\x7f\xb0"  # And
OR =            b"\x7f\xb1"  # Or

NOT =           b"\x7f\xb3"  # Not
XOR =           b"\x7f\xb4"  # Xor

INT_DIVIDE =    b"\x7f\xbc"  # Int÷

SIN =           b"\x81"  # sin
COS =           b"\x82"  # cos
TAN =           b"\x83"  # tan

LN =            b"\x85"  # ln
SQUARE_ROOT =   b"\x86"  # √
NEGATIVE =      b"\x87"  # ‑

ADD =           b"\x89"  # +

SQUARED =       b"\x8b"  # ²

ARCSIN =        b"\x91"  # sin⁻¹
ARCCOS =        b"\x92"  # cos⁻¹
ARCTAN =        b"\x93"  # tan⁻¹

LOG =           b"\x95"  # log
CUBE_ROOT =     b"\x96"  # ³√
ABSOLUTE =      b"\x97"  # Abs

SUBTRACT =      b"\x99"  # -

INVERSE =       b"\x9b"  # ⁻¹

SINH =          b"\xa1"  # sinh
COSH =          b"\xa2"  # cosh
TANH =          b"\xa3"  # tanh

E_POWER =       b"\xa5"  # e^
INT =           b"\xa6"  # Int

POWER =         b"\xa8"  # ^
MULTIPLY =      b"\xa9"  # ×

FACTORIAL =     b"\xab"  # !

ARCSINH =       b"\xb1"  # sinh⁻¹
ARCCOSH =       b"\xb2"  # cosh⁻¹
ARCTANH =       b"\xb3"  # tanh⁻¹

TEN_POWER =     b"\xb5"  # ₁₀

XTH_ROOT =      b"\xb8"  # ᕽ√
DIVIDE =        b"\xb9"  # ÷

FRACTION =      b"\xbb"  # ⌟

ANSWER =        b"\xc0"  # Ans
RAND_FLOAT =    b"\xc1"  # Ran#

RADIUS =        b"\xcd"  # r
THETA =         b"\xce"  # θ

PI =            b"\xd0"  # π

FLOOR =         b"\xde"  # Intg

LABEL =         b"\xe2"  # Lbl

DECREMENT =     b"\xe8"  # Dsz
INCREMENT =     b"\xe9"  # Isz

GOTO =          b"\xec"  # Goto

PROGRAM =       b"\xed"  # Prog

IF =            b"\xf7\x00"  # If
THEN =          b"\xf7\x01"  # Then
ELSE =          b"\xf7\x02"  # Else
IF_END =        b"\xf7\x03"  # IfEnd
FOR =           b"\xf7\x04"  # For
TO =            b"\xf7\x05"  # To
STEP =          b"\xf7\x06"  # Step
NEXT =          b"\xf7\x07"  # Next
WHILE =         b"\xf7\x08"  # While
WHILE_END =     b"\xf7\x09"  # WhileEnd
DO =            b"\xf7\x0a"  # Do
LOOP_WHILE =    b"\xf7\x0b"  # LpWhile
RETURN =        b"\xf7\x0c"  # Return
BREAK =         b"\xf7\x0d"  # Break
STOP =          b"\xf7\x0e"  # Stop

LOCATE =        b"\xf7\x10"  # Locate

CLR_TEXT =      b"\xf7\x18"  # ClrText
CLR_GRAPH =     b"\xf7\x19"  # ClrGraph

CLR_LIST =      b"\xf7\x1a"  # ClrList

CLR_MATRIX =    b"\xf9\x1e"  # ClrMat

STR_JOIN =      b"\xf9\x30"  # StrJoin(
STR_LENGTH =    b"\xf9\x31"  # StrLen(
STR_COMPARE =   b"\xf9\x32"  # StrCmp(
STR_SEARCH =    b"\xf9\x33"  # StrSrc(
STR_LEFT =      b"\xf9\x34"  # StrLeft(
STR_RIGHT =     b"\xf9\x35"  # StrRight(
STR_MID =       b"\xf9\x36"  # StrMid(
EXP_TO_STR =    b"\xf9\x37"  # Exp⏵Str(
EXPRESSION =    b"\xf9\x38"  # Exp(
STR_UPPER =     b"\xf9\x39"  # StrUpr(
STR_LOWER =     b"\xf9\x3a"  # StrLwr(
STR_INVERSE =   b"\xf9\x3b"  # StrInv(
STR_SHIFT =     b"\xf9\x3c"  # StrShift(
STR_ROTATE =    b"\xf9\x3d"  # StrRotate(

STRING =        b"\xf9\x3f"  # Str

MENU =          b"\xf7\x9e"  # Menu

"""
Known to be normal ASCII (i.e. calling s.encode() or using byte notation b"..." is enough)
type        | full list of examples
------------+-----------------------
numbers     | 0 1 2 3 4 5 6 7 8 9
alphabet    | A B C D E F G H I J K L M N O P Q R S T U V W X Y Z
literal ' ' |  
grouping    | ( ) { } [ ]
symbols     | 
comparison  | = < >
punctuation | , . ? : "
"""
