USE  cryptrade;

DROP VIEW IF EXISTS transaction_view;
DROP VIEW IF EXISTS datafetch_api_response_view;
DROP VIEW IF EXISTS datafetch_api_view;
DROP VIEW IF EXISTS transaction_price_range_view;

DROP TABLE IF EXISTS datafetch_api_response_view;
DROP TABLE IF EXISTS datafetch_api_response;
DROP TABLE IF EXISTS datafetch_file;
DROP TABLE IF EXISTS transaction;
DROP TABLE IF EXISTS datasource;
DROP TABLE IF EXISTS currency;
DROP TABLE IF EXISTS exchange;
DROP TABLE IF EXISTS datafetch_api;
DROP TABLE IF EXISTS feature_value;
DROP TABLE IF EXISTS feature;

DROP FUNCTION IF EXISTS datasource_id_by_name;
DROP FUNCTION IF EXISTS currency_id_by_name;
DROP FUNCTION IF EXISTS exchange_id_by_name;
DROP FUNCTION IF EXISTS feature_id_by_name;
DROP FUNCTION IF EXISTS feature_value_id_by_name;



CREATE TABLE exchange (
	id INT NOT NULL AUTO_INCREMENT,
    name VARCHAR(255),
    epoch_createtime TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
	);

CREATE TABLE  currency (
	id INT NOT NULL AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(3) NOT NULL,
    is_crypto BOOLEAN NOT NULL,
    epoch_createtime TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
	);

-- DROP TABLE datasource
CREATE TABLE datasource (
	id INT NOT NULL AUTO_INCREMENT,
    name VARCHAR(255),
    epoch_createtime TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
	);

-- DROP TABLE crypto_transaction;
CREATE TABLE transaction (
	id INT NOT NULL AUTO_INCREMENT,
	datasource_id INT NOT NULL,
    exchange_id INT NOT NULL,
    from_currency_id INT NOT NULL,
    to_currency_id INT NOT NULL,
    amount decimal(25,16) NOT NULL,
    price decimal(25,16) NOT NULL,
    volume decimal(20,8) NULL,
    volume_percent float(7,4) NULL,
    epoch_time INT(11)  NOT NULL,
	source_md5hash VARCHAR(32) NOT NULL,
    epoch_createtime TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (datasource_id) REFERENCES datasource(id),
    FOREIGN KEY (exchange_id) REFERENCES exchange(id),
    FOREIGN KEY (from_currency_id) REFERENCES currency(id),
    FOREIGN KEY (to_currency_id) REFERENCES currency(id),
    PRIMARY KEY (id)
	);

CREATE UNIQUE INDEX transaction_unique_index ON transaction(
	datasource_id, 
    exchange_id, 
    from_currency_id,
    to_currency_id,
    amount, 
    price, 
    epoch_time
    );

CREATE INDEX transaction_index_epoch_time ON transaction(
	epoch_time
	);

CREATE INDEX transaction_source_md5hash ON transaction(
	source_md5hash
	);



DELIMITER $$

CREATE FUNCTION datasource_id_by_name (name VARCHAR(255)) RETURNS INT DETERMINISTIC
BEGIN 
	DECLARE result INT;
	SELECT id INTO result FROM datasource WHERE datasource.name = name;
	RETURN result;
END$$
CREATE FUNCTION currency_id_by_name(name VARCHAR(255)) RETURNS INT DETERMINISTIC
BEGIN
	DECLARE result INT;	
	SELECT id INTO result FROM currency WHERE currency.code = name;
	RETURN result;
END$$
CREATE FUNCTION exchange_id_by_name(name VARCHAR(255)) RETURNS INT DETERMINISTIC
BEGIN
	DECLARE result INT;	
	SELECT id INTO result FROM exchange WHERE exchange.name = name;
	RETURN result;
END$$
CREATE FUNCTION feature_id_by_name(name VARCHAR(255)) RETURNS INT DETERMINISTIC
BEGIN
	DECLARE result INT;	
	SELECT id INTO result FROM feature WHERE feature.name = name;
	RETURN result;
END$$
CREATE FUNCTION feature_value_id_by_name(name VARCHAR(255)) RETURNS INT DETERMINISTIC
BEGIN
	DECLARE result INT;	
	SELECT id INTO result FROM feature_value WHERE feature_value.name = name;
	RETURN result;
END$$

DELIMITER ;

CREATE TABLE datafetch_file (
	id INT NOT NULL AUTO_INCREMENT,
	datasource_id INT NOT NULL,
	exchange_id INT NOT NULL,
	from_currency_id INT NOT NULL,
	to_currency_id INT NOT NULL,
	data_url VARCHAR(1024) NOT NULL,
	frequency VARCHAR(64) NOT NULL,
	handler_filepath VARCHAR(1024) NOT NULL,
    epoch_createtime TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (from_currency_id) REFERENCES currency(id),
    FOREIGN KEY (to_currency_id) REFERENCES currency(id),
	PRIMARY KEY (id)
	);

CREATE TABLE datafetch_api (
	id INT NOT NULL AUTO_INCREMENT,
	handler_filepath VARCHAR(1024) NOT NULL,
	result_endpoint VARCHAR(255) NULL,
	result_frequency_seconds INT NULL DEFAULT 30,
    epoch_createtime TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id)
	);

CREATE TABLE datafetch_api_response (
	id INT NOT NULL AUTO_INCREMENT,
	datafetch_api_id INT NOT NULL,
	datasource_id INT NOT NULL,
	exchange_id INT NOT NULL,
	from_currency_id INT NOT NULL,
	to_currency_id INT NOT NULL,
	response TEXT NOT NULL,
	response_md5hash VARCHAR(32) NOT NULL,
	response_filename VARCHAR(1024) NOT NULL,
    epoch_receive_time INT(11)  NOT NULL,
    epoch_createtime TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    FOREIGN KEY (from_currency_id) REFERENCES currency(id),
    FOREIGN KEY (to_currency_id) REFERENCES currency(id),
    FOREIGN KEY (datafetch_api_id) REFERENCES datafetch_api(id),
	PRIMARY KEY (id)
	);

CREATE UNIQUE INDEX datafetch_api_response_unique_index ON datafetch_api_response(
	datafetch_api_id,
	datasource_id,
	exchange_id,
	from_currency_id,
	to_currency_id,
	response_md5hash,
    epoch_receive_time
	);

CREATE UNIQUE INDEX datafetch_api_response_response_filename_unique_index ON datafetch_api_response(
	response_filename
	);

CREATE INDEX datafetch_api_response_index_epoch_receive_time ON datafetch_api_response(
    epoch_receive_time
	);

CREATE INDEX datafetch_api_response_index_response_md5hash ON datafetch_api_response(
    response_md5hash
	);

CREATE VIEW datafetch_api_view AS
	SELECT 
		datafetch_api.*,
		datafetch_api_response.epoch_createtime AS latest_response_createtime,
        TIMESTAMPDIFF(second, datafetch_api_response.epoch_createtime, CURRENT_TIMESTAMP) AS write_idle_seconds
	FROM datafetch_api
	LEFT JOIN datafetch_api_response ON
			   datafetch_api_response.datafetch_api_id = datafetch_api.id
	WHERE
		datafetch_api_response.epoch_createtime IS NULL 
	OR 
		datafetch_api_response.id = ( 
			SELECT id FROM datafetch_api_response
            	WHERE id = datafetch_api_response.id
                AND datafetch_api_id = datafetch_api.id
                ORDER BY epoch_createtime DESC
                LIMIT 1
            )
    ;

CREATE VIEW datafetch_api_response_view AS
	SELECT datafetch_api.handler_filepath as handler_filepath,
		   datasource.name AS datasource_name,
		   exchange.name AS provider_name,
		   from_currency.code AS from_currency_code,
		   to_currency.code AS to_currency_code,
		   response,
		   response_md5hash,
		   datafetch_api_response.epoch_createtime
	FROM datafetch_api_response
	INNER JOIN datafetch_api ON 
			   datafetch_api.id = datafetch_api_response.datafetch_api_id
	INNER JOIN datasource ON 
			   datasource.id = datafetch_api_response.datasource_id
	INNER JOIN exchange ON	
		       exchange.id = datafetch_api_response.exchange_id
	INNER JOIN currency AS from_currency ON
			   			   from_currency.id = datafetch_api_response.from_currency_id
	INNER JOIN currency AS to_currency ON
			   			   to_currency.id = datafetch_api_response.to_currency_id
	;			   


CREATE TABLE feature (
	id INT NOT NULL AUTO_INCREMENT,
	name VARCHAR(128) NOT NULL,
	PRIMARY KEY (id)
	);
CREATE UNIQUE INDEX feature_unique_index ON feature(name);

CREATE TABLE feature_value (
	id INT NOT NULL AUTO_INCREMENT,
	feature_id INT NOT NULL,
	name VARCHAR(128) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY	(feature_id) REFERENCES feature(id)
	);
CREATE UNIQUE INDEX feature_value_unique_index ON feature_value(feature_id, name);
	
CREATE VIEW transaction_price_range_view AS 
	SELECT 
		transaction.from_currency_id,
		transaction.to_currency_id,    
	    MAX(transaction.price) AS high,
	    MIN(transaction.price) AS low,
	    AVG(transaction.price) AS avg,
	    from_unixtime(MIN(transaction.epoch_time)) AS opentime,
	    from_unixtime(MAX(transaction.epoch_time)) AS closetime
	FROM transaction 
	GROUP BY 
		transaction.from_currency_id, 
		transaction.to_currency_id
	; 


CREATE VIEW transaction_view AS
	SELECT transaction.id,
		   datasource.name AS datasource_name,
		   exchange.name AS provider_name,
		   from_currency.code AS from_currency_code,
		   to_currency.code AS to_currency_code,
		   transaction.amount AS amount,
		   transaction.price AS price,
		   from_unixtime(transaction.epoch_time) as time,
		   transaction.epoch_createtime as createtime,		   
		   datafetch_api_response.id as datafetch_api_response_id
	FROM transaction
	INNER JOIN datasource ON 
			datasource.id = transaction.datasource_id
	INNER JOIN exchange ON	
			exchange.id = transaction.exchange_id
	INNER JOIN currency AS from_currency ON
			from_currency.id = transaction.from_currency_id
	INNER JOIN currency AS to_currency ON
   			to_currency.id = transaction.to_currency_id
	LEFT JOIN datafetch_api_response ON
		    datafetch_api_response.response_md5hash = transaction.source_md5hash
	;			   


-- -----------------------------------------
-- INSERTS ---------------------------------
-- -----------------------------------------

INSERT INTO feature (name) VALUES 
	('trend'), 
	('moving average crossover'), 
	('candlestick'), 
	('stochastic'), 
	('volume'), 
	('adx')
	;

INSERT INTO feature_value (feature_id, name) VALUES
	(feature_id_by_name('trend'), 'up'),
	(feature_id_by_name('trend'), 'down'),
	(feature_id_by_name('trend'), 'level'),
	(feature_id_by_name('moving average crossover'), 'buy'),
	(feature_id_by_name('moving average crossover'), 'sell'),
	(feature_id_by_name('moving average crossover'), 'hold'),
	(feature_id_by_name('candlestick'), 'buy'),
	(feature_id_by_name('candlestick'), 'sell'),
	(feature_id_by_name('candlestick'), 'hold'),
	(feature_id_by_name('stochastic'), 'buy'),
	(feature_id_by_name('stochastic'), 'sell'),
	(feature_id_by_name('stochastic'), 'hold'),
	(feature_id_by_name('volume'), 'strong'),
	(feature_id_by_name('volume'), 'weak'),
	(feature_id_by_name('adx'), 'strong'),
	(feature_id_by_name('adx'), 'weak')
	;

INSERT INTO exchange (name) VALUES ('bitstamp');    
INSERT INTO exchange (name) VALUES ('coinbase');    
INSERT INTO exchange (name) VALUES ('multiple_local');    
INSERT INTO exchange (name) VALUES ('multiple_global');    

INSERT INTO currency (name, code, is_crypto) VALUES ('US Dollars', 'USD', 0);
INSERT INTO currency (name, code, is_crypto) VALUES ('Euros', 'EUR', 0);
INSERT INTO currency (name, code, is_crypto) VALUES ('Bitcoin', 'BTC', 1);
INSERT INTO currency (name, code, is_crypto) VALUES ('Bitcoin Cash', 'BCH', 1);
INSERT INTO currency (name, code, is_crypto) VALUES ('Ripple', 'XRP', 1);
INSERT INTO currency (name, code, is_crypto) VALUES ('Ethereum', 'ETH', 1);
INSERT INTO currency (name, code, is_crypto) VALUES ('Litecoin', 'LTC', 1);

INSERT INTO datasource (name) VALUES ('bitcoincharts');    
INSERT INTO datasource (name) VALUES ('bitcoinaverage');    
INSERT INTO datasource (name) VALUES ('openexchange');    
