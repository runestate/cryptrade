# cryptrade
An full-fledged investment platform that uses historical trading data to perform financial technical analysis and predict future market trends. This is not a commercial tool, but merely techniques I use for personal investments.


## Technologies
This solution is based on python and bash for execution in EC2,   Tensorflow/AWS SageMaker for DNN, HDF5, MySQL and S3 for storage.


## Motivation
Technical analysis is an old discipline, but has recently become an attractive tool for predicting short-term swing trades as real-time price and volume data have become broadly available. From this data indicators can be extracted, such as whether to buy or sell, if the current trend is up or down and whether or not these trends are strong. Training a powerful deep neural network on this data is now possible with cloud-based services.


## Feature agents
The system uses the following well-known concepts as feature agents:

* moving average crossover
* candlestick patterns
* stochastic oscillator
* adx
* volume
* trend

When presented with a new observation of live trading data, each of these agents generate a value from a discrete set of possible feature values, i.e. each observation of trading data maps to a set of indicator values.



## High-level data pipeline

The pipeline is designed as loosely sketched here:

1: live data observation --> `s3` --> 2: clean + parse --> `RDBMS` --> 3: feature derivation --> `HDF5` --> 4: refine model and potentially invest or divest

Steps:

1.  incoming raw data is stored in persistant storage
2. the data is processed, e.g. to filter out duplicate observations, and stored in a format that allows for complex querying
3. feature agents produce a set of feature values
4. the neural network is presented with a set of feature values (one-hot encoded) and generates investment advice via ensemble learning


## Modules
The system comprises of the following modules to achieve automation and inspection.

### components
* fetch: a process that continuously retrieves and persists (raw) live trading data
* s3push: a process that continuously archives raw data to s3
* parse: a process that parses new raw trading data whenever such is detected
* generator: a process that generate feature values whenever a new (parsed/cleaned) data observation is detected
* predict: a process that produces investment advice whenever a new set of feature values is detected
* watch: a process that monitors for stale data and log errors
* alert: a process that monitors key sources of information on the future of trading commodities (e.g. regulatory branches of the federal government)
* plotserve: a graph-based UI for inspecting the incoming data and the behavior of the feature agents derived thereof

