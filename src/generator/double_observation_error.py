class DoubleObservationError(Exception):
	def __init__(self, epoch):
		super().__init__('Double oservation for epoch {}'.format(epoch))
