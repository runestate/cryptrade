from candlestick_pattern import CandlestickPattern
from numpy import float64

class DowntrendReversalPattern:
	@staticmethod
	def pattern(t1, t2, t3):
		if DowntrendReversalPattern.__is_hammer(t1, t2, t3) == True:
			return CandlestickPattern.HAMMER
		if DowntrendReversalPattern.__is_bullish_engulf(t1, t2, t3) == True:
			return CandlestickPattern.BULLISH_ENGULF
		if DowntrendReversalPattern.__is_three_white_soldiers(t1, t2, t3) == True:
			return CandlestickPattern.THREE_WHITE_SOLDIERS
		if DowntrendReversalPattern.__is_three_inside_up(t1, t2, t3) == True:
			return CandlestickPattern.THREE_INSIDE_UP
		if DowntrendReversalPattern.__is_morning_star(t1, t2, t3) == True:
			return CandlestickPattern.IS_MORNING_STAR
		return None
	@staticmethod
	def __is_hammer(t1, t2, t3):
		return (
			t1.is_white == 1 and 
			t1.lower_shadow >= 2 * t1.body and 
			t1.upper_shadow <= 0.05 and 
			t1.body >= 0.1
			)
	@staticmethod
	def __is_bullish_engulf(t1, t2, t3):
		return (
			t2.is_black == 1 and 
			t1.is_white == 1 and 
			t1.open <= t2.close and 
			t1.close >= t2.open
			)
	@staticmethod
	def __is_three_white_soldiers(t1, t2, t3):
		return (
			t1.is_white == 1 and 
			t2.is_white == 1 and 
			t3.is_white == 1 and 
			t1.open > t2.open and 
			t2.open > t3.open and 
			t1.close > t2.close and 
			t2.close > t3.close
			)
	@staticmethod
	def __is_three_inside_up(t1, t2, t3):
		return (
			t3.is_black == 1 and 
			t3.body > 0.8 and #  large real body, TODO: how to formalize?
			t2.is_white == 1 and
			t2.open > t3.close and
			t2.close < t3.open and
			t1.is_white == 1 and 
			t1.close > t2.close
			)
	@staticmethod
	def __is_morning_star(t1, t2, t3):
		return (
			t3.is_black == 1 and
			t2.close < t3.close and
			t1.is_white == 1 and
			t1.open > t2.close and
			t1.body >= float64(2/3) * t3.body 
			)
