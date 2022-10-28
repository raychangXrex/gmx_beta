use glp_database;
create table summary_total_balance(
id int not null auto_increment,
created_date datetime not null,
updated_date datetime not null,
exchange_name varchar(32) not null,
notional decimal(32, 16) not null,
wallet_balance decimal(32, 16) not null,
margin_ratio decimal(32, 16) not null,
primary key(id) 
)ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;

create table binance_hedge_account(
id int not null auto_increment,
created_date datetime not null,
updated_date datetime not null,
position_amount decimal(32,16) not null,
notional decimal(32,16) not null,
funding_rate decimal(32,16) not null,
quote varchar(32) not null,
base varchar(32) not null,
unrealized_profit decimal(32) not null,
primary key(id) 
)ENGINE=InnoDB AUTO_INCREMENT=1;

create table gmx_account 
(
id int not null auto_increment,
created_date datetime not null,
updated_date datetime not null,
position_amount decimal(32,16) not null,
notional decimal(32,16) not null,
symbol varchar(32) not null,
claimable decimal(32,16) not null,
cumulative decimal(32,16) not null,
primary key(id)
)ENGINE=InnoDB AUTO_INCREMENT=1;

create table metamask_account(
id int not null auto_increment,
created_date datetime not null,
updated_date datetime not null,
amount decimal(32,16) not null,
notional decimal(32,16) not null,
symbol varchar(32) not null,
primary key(id)
)ENGINE=InnoDB AUTO_INCREMENT=1;