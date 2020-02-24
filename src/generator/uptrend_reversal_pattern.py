from candlestick_pattern import CandlestickPattern
from numpy import float64

class UptrendReversalPattern:
	@staticmethod
	def pattern(t1, t2, t3):
		if UptrendReversalPattern.__is_hanging_man(t1, t2, t3) == True:
			return CandlestickPattern.HANGING_MAN
		if UptrendReversalPattern.__is_three_inside_down(t1, t2, t3) == True:
			return CandlestickPattern.THREE_INSIDE_DOWN
		if UptrendReversalPattern.__is_three_black_crows(t1, t2, t3) == True:
			return CandlestickPattern.THREE_BLACK_CROWS
		if UptrendReversalPattern.__is_evening_star(t1, t2, t3) == True:
			return CandlestickPattern.EVENING_STAR
		if UptrendReversalPattern.__is_bearish_engulfing(t1, t2, t3) == True:
			return CandlestickPattern.BEARISH_ENGULFING
		return None
	@staticmethod
	def __is_hanging_man(t1, t2, t3):
		return (
			t1.is_black == 1 and 
			t1.lower_shadow >= 2 * t1.body and 
			t1.upper_shadow <= 0.05 and 
			t1.body >= 0.1
			)
	def __is_three_inside_down(t1, t2, t3):
		return (
			t3.is_white == 1 and 
			t3.body > 0.8 and #  large real body, TODO: how to formalize?
			t2.is_black == 1 and
			t2.open > t3.close and
			t2.close < t3.open and
			t1.is_black == 1 and 
			t1.close < t2.close
			)
	@staticmethod
	def __is_three_black_crows(t1, t2, t3):
		return (
			t1.is_black == 1 and 
			t2.is_black == 1 and 
			t3.is_black == 1 and 
			t1.open < t2.open and 
			t1.close < t2.close and 
			t2.open < t3.open and 
			t2.close < t3.close
			)
	@staticmethod
	def __is_evening_star(t1, t2, t3):
		return (
			t3.is_white == 1 and 
			t2.close > t3.high and 
			t1.is_black == 1 and
			t1.open < t2.close and
			t1.body >= float64(2/3) * t3.body 
			)
	@staticmethod
	def __is_bearish_engulfing(t1, t2, t3):
		return (
			t1.is_black == 1 and
			t2.is_white == 1 and
			t1.open > t2.open and
			t1.close < t2.close 
			)
