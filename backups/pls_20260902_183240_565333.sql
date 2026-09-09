PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL, 
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
INSERT INTO "alembic_version" VALUES('010_warehouse_staff_fot');
CREATE TABLE billing_periods (
	id INTEGER NOT NULL, 
	contract_id INTEGER NOT NULL, 
	period_year INTEGER NOT NULL, 
	period_month INTEGER NOT NULL, 
	status VARCHAR(32) DEFAULT 'draft' NOT NULL, 
	total_ex_vat NUMERIC(14, 2), 
	locked_by INTEGER, 
	locked_at DATETIME, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_billing_period_contract_ym UNIQUE (contract_id, period_year, period_month), 
	FOREIGN KEY(contract_id) REFERENCES contracts (id), 
	FOREIGN KEY(locked_by) REFERENCES users (id)
);
INSERT INTO "billing_periods" VALUES(1,2,2026,8,'draft',12153206.9,NULL,NULL,'2026-09-02 12:35:06.820124','2026-09-02 14:49:44.348113');
INSERT INTO "billing_periods" VALUES(2,2,2026,9,'draft',6793638.08,NULL,NULL,'2026-09-02 12:35:13.485882','2026-09-02 14:49:29.873595');
CREATE TABLE clients (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	security_name VARCHAR(255), 
	is_active BOOLEAN DEFAULT 1 NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME, 
	PRIMARY KEY (id)
);
INSERT INTO "clients" VALUES(1,'ООО "Аристон Термо Русь"','Аристон',1,'2026-09-02 04:33:32.277554','2026-09-02 10:43:40.515432');
CREATE TABLE contract_amendments (
	id INTEGER NOT NULL, 
	contract_id INTEGER NOT NULL, 
	number VARCHAR(64) NOT NULL, 
	status VARCHAR(32) DEFAULT 'active' NOT NULL, 
	effective_from DATE NOT NULL, 
	effective_to DATE, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME, source_file_path VARCHAR(512), 
	PRIMARY KEY (id), 
	FOREIGN KEY(contract_id) REFERENCES contracts (id)
);
INSERT INTO "contract_amendments" VALUES(1,2,'ДС-6/2024','draft','2026-08-01',NULL,'2026-09-02 15:23:43.600900','2026-09-02 15:23:43.865436','uploads\amendments\1_No6____010926__..docx');
CREATE TABLE contracts (
	id INTEGER NOT NULL, 
	client_id INTEGER NOT NULL, 
	warehouse_id INTEGER NOT NULL, 
	product_type_id INTEGER NOT NULL, 
	number VARCHAR(64) NOT NULL, 
	status VARCHAR(32) DEFAULT 'active' NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME, billing_config JSON, 
	PRIMARY KEY (id), 
	FOREIGN KEY(client_id) REFERENCES clients (id), 
	FOREIGN KEY(product_type_id) REFERENCES product_types (id), 
	FOREIGN KEY(warehouse_id) REFERENCES warehouses (id)
);
INSERT INTO "contracts" VALUES(2,1,2,1,'№ АР-БСХ 24 от 06 июня 2024','active','2026-09-02 06:24:03.600012','2026-09-02 14:16:57.716768','{"area_mode": "two_tier", "fixed_m2days": 9435}');
CREATE TABLE operation_daily_totals (
	id INTEGER NOT NULL, 
	contract_id INTEGER NOT NULL, 
	warehouse_id INTEGER NOT NULL, 
	report_date DATE NOT NULL, 
	billing_line_code VARCHAR(64) NOT NULL, 
	quantity NUMERIC(14, 3) DEFAULT '0' NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(contract_id) REFERENCES contracts (id), 
	FOREIGN KEY(warehouse_id) REFERENCES warehouses (id), 
	CONSTRAINT uq_operation_daily_totals_contract_date_code UNIQUE (contract_id, report_date, billing_line_code)
);
INSERT INTO "operation_daily_totals" VALUES(1,1,1,'2026-08-15','valve_gluing',120,'2026-09-02 04:33:32.352573');
INSERT INTO "operation_daily_totals" VALUES(2,2,2,'2026-08-03','valve_gluing',54,'2026-09-02 09:33:56.977885');
INSERT INTO "operation_daily_totals" VALUES(3,2,2,'2026-08-04','valve_gluing',54,'2026-09-02 09:33:56.977891');
INSERT INTO "operation_daily_totals" VALUES(4,2,2,'2026-08-05','valve_gluing',54,'2026-09-02 09:33:56.977895');
INSERT INTO "operation_daily_totals" VALUES(5,2,2,'2026-08-06','valve_gluing',54,'2026-09-02 09:33:56.977898');
INSERT INTO "operation_daily_totals" VALUES(6,2,2,'2026-08-07','valve_gluing',54,'2026-09-02 09:33:56.977901');
INSERT INTO "operation_daily_totals" VALUES(7,2,2,'2026-08-10','valve_gluing',54,'2026-09-02 09:33:56.977904');
INSERT INTO "operation_daily_totals" VALUES(8,2,2,'2026-08-11','valve_gluing',54,'2026-09-02 09:33:56.977907');
INSERT INTO "operation_daily_totals" VALUES(9,2,2,'2026-08-12','valve_gluing',54,'2026-09-02 09:33:56.977910');
INSERT INTO "operation_daily_totals" VALUES(10,2,2,'2026-08-13','valve_gluing',54,'2026-09-02 09:33:56.977913');
INSERT INTO "operation_daily_totals" VALUES(11,2,2,'2026-08-14','valve_gluing',54,'2026-09-02 09:33:56.977916');
INSERT INTO "operation_daily_totals" VALUES(12,2,2,'2026-08-17','valve_gluing',54,'2026-09-02 09:33:56.977920');
INSERT INTO "operation_daily_totals" VALUES(13,2,2,'2026-08-18','valve_gluing',54,'2026-09-02 09:33:56.977923');
INSERT INTO "operation_daily_totals" VALUES(14,2,2,'2026-08-19','valve_gluing',54,'2026-09-02 09:33:56.977926');
INSERT INTO "operation_daily_totals" VALUES(15,2,2,'2026-08-20','valve_gluing',54,'2026-09-02 09:33:56.977929');
INSERT INTO "operation_daily_totals" VALUES(16,2,2,'2026-08-21','valve_gluing',54,'2026-09-02 09:33:56.977934');
INSERT INTO "operation_daily_totals" VALUES(17,2,2,'2026-08-24','valve_gluing',54,'2026-09-02 09:33:56.977937');
INSERT INTO "operation_daily_totals" VALUES(18,2,2,'2026-08-25','valve_gluing',54,'2026-09-02 09:33:56.977940');
INSERT INTO "operation_daily_totals" VALUES(19,2,2,'2026-08-26','valve_gluing',51,'2026-09-02 09:33:56.977943');
INSERT INTO "operation_daily_totals" VALUES(20,2,2,'2026-08-27','valve_gluing',51,'2026-09-02 09:33:56.977946');
INSERT INTO "operation_daily_totals" VALUES(21,2,2,'2026-08-28','valve_gluing',51,'2026-09-02 09:33:56.977960');
INSERT INTO "operation_daily_totals" VALUES(22,2,2,'2026-08-31','valve_gluing',51,'2026-09-02 09:33:56.977963');
INSERT INTO "operation_daily_totals" VALUES(23,2,2,'2026-08-03','flue_stickering',228,'2026-09-02 09:33:56.977966');
INSERT INTO "operation_daily_totals" VALUES(24,2,2,'2026-08-04','flue_stickering',228,'2026-09-02 09:33:56.977971');
INSERT INTO "operation_daily_totals" VALUES(25,2,2,'2026-08-05','flue_stickering',228,'2026-09-02 09:33:56.977974');
INSERT INTO "operation_daily_totals" VALUES(26,2,2,'2026-08-06','flue_stickering',228,'2026-09-02 09:33:56.977977');
INSERT INTO "operation_daily_totals" VALUES(27,2,2,'2026-08-07','flue_stickering',228,'2026-09-02 09:33:56.977989');
INSERT INTO "operation_daily_totals" VALUES(28,2,2,'2026-08-10','flue_stickering',228,'2026-09-02 09:33:56.977992');
INSERT INTO "operation_daily_totals" VALUES(29,2,2,'2026-08-11','flue_stickering',228,'2026-09-02 09:33:56.977995');
INSERT INTO "operation_daily_totals" VALUES(30,2,2,'2026-08-12','flue_stickering',228,'2026-09-02 09:33:56.977997');
INSERT INTO "operation_daily_totals" VALUES(31,2,2,'2026-08-13','flue_stickering',228,'2026-09-02 09:33:56.978000');
INSERT INTO "operation_daily_totals" VALUES(32,2,2,'2026-08-14','flue_stickering',228,'2026-09-02 09:33:56.978003');
INSERT INTO "operation_daily_totals" VALUES(33,2,2,'2026-08-17','flue_stickering',228,'2026-09-02 09:33:56.978005');
INSERT INTO "operation_daily_totals" VALUES(34,2,2,'2026-08-18','flue_stickering',228,'2026-09-02 09:33:56.978008');
INSERT INTO "operation_daily_totals" VALUES(35,2,2,'2026-08-19','flue_stickering',228,'2026-09-02 09:33:56.978011');
INSERT INTO "operation_daily_totals" VALUES(36,2,2,'2026-08-20','flue_stickering',228,'2026-09-02 09:33:56.978015');
INSERT INTO "operation_daily_totals" VALUES(37,2,2,'2026-08-21','flue_stickering',228,'2026-09-02 09:33:56.978018');
INSERT INTO "operation_daily_totals" VALUES(38,2,2,'2026-08-24','flue_stickering',228,'2026-09-02 09:33:56.978021');
INSERT INTO "operation_daily_totals" VALUES(39,2,2,'2026-08-25','flue_stickering',228,'2026-09-02 09:33:56.978023');
INSERT INTO "operation_daily_totals" VALUES(40,2,2,'2026-08-26','flue_stickering',228,'2026-09-02 09:33:56.978026');
INSERT INTO "operation_daily_totals" VALUES(41,2,2,'2026-08-27','flue_stickering',228,'2026-09-02 09:33:56.978029');
INSERT INTO "operation_daily_totals" VALUES(42,2,2,'2026-08-28','flue_stickering',228,'2026-09-02 09:33:56.978032');
INSERT INTO "operation_daily_totals" VALUES(43,2,2,'2026-08-31','flue_stickering',225,'2026-09-02 09:33:56.978034');
CREATE TABLE process_line_config (
	id INTEGER NOT NULL, 
	process_line_id INTEGER NOT NULL, 
	config_json JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(process_line_id) REFERENCES process_lines (id), 
	UNIQUE (process_line_id)
);
INSERT INTO "process_line_config" VALUES(1,1,'{"enabled_sections": ["period_inputs", "day_confirm"], "extra_billing_line_codes": ["valve_gluing"], "form_fields": [{"billing_line_code": "valve_gluing", "label": "\u041f\u043e\u0434\u043a\u043b\u0435\u0439\u043a\u0430 \u043a\u043b\u0430\u043f\u0430\u043d\u043e\u0432", "input_kind": "period", "quantity_source": "manual_daily"}], "ui_labels": {"title": "\u0421\u043a\u043b\u0430\u0434 \u0410\u0440\u0438\u0441\u0442\u043e\u043d"}}');
INSERT INTO "process_line_config" VALUES(2,2,'{"enabled_sections": ["vehicle_operations", "period_inputs", "day_confirm"], "extra_billing_line_codes": ["custom_waybill_type"], "form_fields": [{"field": "waybill_doc_type", "label": "\u0422\u0438\u043f \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430", "section": "vehicle_operations"}], "validation_rules": {"waybill_doc_type": {"required": true}}, "ui_labels": {"title": "\u0422\u0440\u0430\u043d\u0441\u043f\u043e\u0440\u0442 \u0413\u0430\u0437\u043f\u0440\u043e\u043c"}}');
CREATE TABLE process_lines (
	id INTEGER NOT NULL, 
	code VARCHAR(64) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	base_process VARCHAR(64) NOT NULL, 
	client_id INTEGER, 
	is_active BOOLEAN DEFAULT 1 NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(client_id) REFERENCES clients (id), 
	UNIQUE (code)
);
INSERT INTO "process_lines" VALUES(1,'ariston_standard','Аристон стандарт','warehouse_logistics',1,1);
INSERT INTO "process_lines" VALUES(2,'gazprom_logistics','Газпром логистика','transport_logistics',NULL,1);
CREATE TABLE product_types (
	id INTEGER NOT NULL, 
	code VARCHAR(32) NOT NULL, 
	name VARCHAR(128) NOT NULL, is_active BOOLEAN DEFAULT 1 NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (code)
);
INSERT INTO "product_types" VALUES(1,'RESPONSIBLE_STORAGE','Ответственное хранение',1);
INSERT INTO "product_types" VALUES(2,'SUBLEASE','Субаренда',0);
INSERT INTO "product_types" VALUES(3,'RENT','Аренда',0);
CREATE TABLE roles (
	id INTEGER NOT NULL, 
	code VARCHAR(64) NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (code)
);
INSERT INTO "roles" VALUES(1,'admin','Администратор');
INSERT INTO "roles" VALUES(2,'supervisor','Руководитель смены');
INSERT INTO "roles" VALUES(3,'transport_logistics','Транспортная логистика');
INSERT INTO "roles" VALUES(4,'warehouse_logistics','Складская логистика');
INSERT INTO "roles" VALUES(5,'inventory_management','Управление запасами');
INSERT INTO "roles" VALUES(6,'commercial_logistics','Коммерческая логистика');
CREATE TABLE section_maintenance (
	id INTEGER NOT NULL, 
	target_type VARCHAR(16) NOT NULL, 
	target_key VARCHAR(64) NOT NULL, 
	message TEXT NOT NULL, 
	is_active BOOLEAN DEFAULT 1 NOT NULL, 
	updated_at DATETIME NOT NULL, 
	updated_by INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(updated_by) REFERENCES users (id), 
	UNIQUE (target_type, target_key)
);
CREATE TABLE section_permissions (
	id INTEGER NOT NULL, 
	role_id INTEGER NOT NULL, 
	section_code VARCHAR(64) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(role_id) REFERENCES roles (id), 
	CONSTRAINT uq_section_permissions_role_section UNIQUE (role_id, section_code)
);
INSERT INTO "section_permissions" VALUES(1,1,'uss_admin');
INSERT INTO "section_permissions" VALUES(2,1,'ref_roles');
INSERT INTO "section_permissions" VALUES(3,1,'ref_contracts');
INSERT INTO "section_permissions" VALUES(4,1,'ref_clients');
INSERT INTO "section_permissions" VALUES(5,1,'ref_locations');
INSERT INTO "section_permissions" VALUES(6,1,'uss_ops_warehouse');
INSERT INTO "section_permissions" VALUES(7,1,'ref_staff');
INSERT INTO "section_permissions" VALUES(8,1,'uss_billing');
INSERT INTO "section_permissions" VALUES(9,1,'uss_ops_inventory');
INSERT INTO "section_permissions" VALUES(10,1,'uss_catalog_staff');
INSERT INTO "section_permissions" VALUES(11,1,'request_analytics');
INSERT INTO "section_permissions" VALUES(12,1,'uss_catalog_clients');
INSERT INTO "section_permissions" VALUES(13,1,'uss_process_lines');
INSERT INTO "section_permissions" VALUES(14,1,'uss_catalog_amendments');
INSERT INTO "section_permissions" VALUES(15,1,'uss_catalog_contracts');
INSERT INTO "section_permissions" VALUES(16,1,'ref_vehicles');
INSERT INTO "section_permissions" VALUES(17,1,'uss_catalog_locations');
INSERT INTO "section_permissions" VALUES(18,1,'uss_catalog_rates');
INSERT INTO "section_permissions" VALUES(19,1,'ref_units');
INSERT INTO "section_permissions" VALUES(20,1,'ref_amendments');
INSERT INTO "section_permissions" VALUES(21,1,'uss_ops_transport');
INSERT INTO "section_permissions" VALUES(22,1,'ref_permissions');
INSERT INTO "section_permissions" VALUES(23,1,'ref_tariff_codes');
INSERT INTO "section_permissions" VALUES(24,1,'uss_catalog_vehicles');
INSERT INTO "section_permissions" VALUES(25,2,'uss_admin');
INSERT INTO "section_permissions" VALUES(26,2,'uss_catalog_locations');
INSERT INTO "section_permissions" VALUES(27,2,'ref_roles');
INSERT INTO "section_permissions" VALUES(28,2,'ref_locations');
INSERT INTO "section_permissions" VALUES(29,2,'uss_process_lines');
INSERT INTO "section_permissions" VALUES(30,2,'ref_permissions');
INSERT INTO "section_permissions" VALUES(31,3,'uss_ops_transport');
INSERT INTO "section_permissions" VALUES(32,3,'requests_transport');
INSERT INTO "section_permissions" VALUES(33,3,'requests_view_all');
INSERT INTO "section_permissions" VALUES(34,3,'uss_catalog_vehicles');
INSERT INTO "section_permissions" VALUES(35,4,'uss_ops_warehouse');
INSERT INTO "section_permissions" VALUES(36,5,'uss_ops_inventory');
INSERT INTO "section_permissions" VALUES(37,6,'request_analytics');
INSERT INTO "section_permissions" VALUES(38,6,'tenders');
INSERT INTO "section_permissions" VALUES(39,6,'ref_contracts');
INSERT INTO "section_permissions" VALUES(40,6,'uss_catalog_clients');
INSERT INTO "section_permissions" VALUES(41,6,'uss_process_lines');
INSERT INTO "section_permissions" VALUES(42,6,'ref_clients');
INSERT INTO "section_permissions" VALUES(43,6,'uss_catalog_amendments');
INSERT INTO "section_permissions" VALUES(44,6,'uss_catalog_contracts');
INSERT INTO "section_permissions" VALUES(45,6,'uss_catalog_rates');
INSERT INTO "section_permissions" VALUES(46,6,'uss_billing');
INSERT INTO "section_permissions" VALUES(47,6,'ref_amendments');
INSERT INTO "section_permissions" VALUES(48,6,'requests_view_all');
INSERT INTO "section_permissions" VALUES(49,6,'ref_tariff_codes');
INSERT INTO "section_permissions" VALUES(50,1,'uss_catalog_vehicle_types');
INSERT INTO "section_permissions" VALUES(51,3,'uss_catalog_vehicle_types');
INSERT INTO "section_permissions" VALUES(52,1,'uss_reports');
INSERT INTO "section_permissions" VALUES(53,6,'uss_reports');
INSERT INTO "section_permissions" VALUES(54,1,'ref_vehicle_types');
CREATE TABLE shift_day_confirmations (
	id INTEGER NOT NULL, 
	warehouse_id INTEGER NOT NULL, 
	report_date DATE NOT NULL, 
	report_role VARCHAR(64) NOT NULL, 
	confirmed_by INTEGER, 
	confirmed_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(confirmed_by) REFERENCES users (id), 
	FOREIGN KEY(warehouse_id) REFERENCES warehouses (id), 
	CONSTRAINT uq_shift_day_confirm_wh_date_role UNIQUE (warehouse_id, report_date, report_role)
);
CREATE TABLE shift_reports (
	id INTEGER NOT NULL, 
	warehouse_id INTEGER NOT NULL, 
	report_date DATE NOT NULL, 
	area_entries JSON, 
	extra_entries JSON, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(warehouse_id) REFERENCES warehouses (id), 
	CONSTRAINT uq_shift_reports_wh_date UNIQUE (warehouse_id, report_date)
);
INSERT INTO "shift_reports" VALUES(1,2,'2026-08-25','{"storage_area_extra": 2300}','{"repack_units": 22}','2026-09-02 14:40:51.316824');
INSERT INTO "shift_reports" VALUES(2,2,'2026-08-26','{"storage_area_extra": 2300}','{"repack_units": 22}','2026-09-02 14:40:51.316835');
INSERT INTO "shift_reports" VALUES(3,2,'2026-08-27','{"storage_area_extra": 2300}','{"repack_units": 21}','2026-09-02 14:40:51.316843');
INSERT INTO "shift_reports" VALUES(4,2,'2026-08-28','{"storage_area_extra": 2300}','{"repack_units": 21}','2026-09-02 14:40:51.316850');
INSERT INTO "shift_reports" VALUES(5,2,'2026-08-31','{"storage_area_extra": 2300}','{"repack_units": 21}','2026-09-02 14:40:51.316860');
CREATE TABLE sso_access_requests (
	id INTEGER NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	raw_identity VARCHAR(255), 
	display_name VARCHAR(255), 
	status VARCHAR(32) DEFAULT 'pending' NOT NULL, 
	login_attempts INTEGER DEFAULT '1' NOT NULL, 
	first_seen_at DATETIME NOT NULL, 
	last_seen_at DATETIME NOT NULL, 
	resolved_at DATETIME, 
	resolved_by INTEGER, 
	admin_note VARCHAR(512), 
	PRIMARY KEY (id), 
	FOREIGN KEY(resolved_by) REFERENCES users (id), 
	UNIQUE (email)
);
CREATE TABLE staff_positions (
	id INTEGER NOT NULL, 
	code VARCHAR(32) NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	is_active BOOLEAN DEFAULT 1, 
	PRIMARY KEY (id), 
	UNIQUE (code)
);
CREATE TABLE tariff_rules (
	id INTEGER NOT NULL, 
	contract_id INTEGER NOT NULL, 
	amendment_id INTEGER NOT NULL, 
	billing_line_code VARCHAR(64) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	unit_id INTEGER, 
	report_role VARCHAR(64), 
	report_scope VARCHAR(64), 
	quantity_source VARCHAR(64), 
	is_custom BOOLEAN DEFAULT 0, 
	price_agreed BOOLEAN DEFAULT 1, 
	sort_order INTEGER DEFAULT '0', 
	valid_from DATE NOT NULL, 
	valid_to DATE, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME, rate_line_code VARCHAR(64), quantity_divisor NUMERIC(12, 3) DEFAULT '1' NOT NULL, rate_ex_vat NUMERIC(14, 4), formula VARCHAR(64), 
	PRIMARY KEY (id), 
	FOREIGN KEY(amendment_id) REFERENCES contract_amendments (id), 
	FOREIGN KEY(contract_id) REFERENCES contracts (id), 
	FOREIGN KEY(unit_id) REFERENCES units_of_measure (id)
);
INSERT INTO "tariff_rules" VALUES(1,2,1,'storage_area_fixed','Хранение на площади 9435 м2 за сутки',1,NULL,'period','auto_contract_param',0,1,11,'2026-08-01',NULL,'2026-09-02 15:23:43.869961','2026-09-02 15:23:43.869967','storage_area_fixed',1,24,'rate_times_days_times_qty');
INSERT INTO "tariff_rules" VALUES(2,2,1,'storage_area_extra','Площадь хранения, дополнительный объём, м²',1,'inventory_management','period','manual_inventory',0,1,12,'2026-08-01',NULL,'2026-09-02 15:23:43.869970','2026-09-02 15:23:43.869973','storage_area_extra',1,24,'rate_times_days_times_qty');
INSERT INTO "tariff_rules" VALUES(3,2,1,'manual_m3','Ручная обработка (вход и выход), м³',3,NULL,'period','auto_vehicle',0,1,20,'2026-08-01',NULL,'2026-09-02 15:23:43.869976','2026-09-02 15:23:43.869979','manual_m3',1,250,'rate_times_qty');
INSERT INTO "tariff_rules" VALUES(4,2,1,'mechanized_m3','Выход/вход продукции коробами за 1м3 Механизированная и ручная обработка ТМЦ подбор заказа, погрузка (выход):',3,NULL,'period','auto_vehicle',0,1,30,'2026-08-01',NULL,'2026-09-02 15:23:43.869982','2026-09-02 15:23:43.869984','mechanized_m3',1,180,'rate_times_qty');
INSERT INTO "tariff_rules" VALUES(5,2,1,'vehicle_docs','Пакет документации на Заказ',5,NULL,'period','auto_vehicle',0,1,40,'2026-08-01',NULL,'2026-09-02 15:23:43.869987','2026-09-02 15:23:43.869989','vehicle_docs',1,109.52,'rate_times_qty');
INSERT INTO "tariff_rules" VALUES(6,2,1,'repack_units','Переупаковка (единиц приборов)',4,'inventory_management','period','manual_inventory',0,1,50,'2026-08-01',NULL,'2026-09-02 15:23:43.869992','2026-09-02 15:23:43.869995','repack_units',1,219.04,'rate_times_qty');
CREATE TABLE units_of_measure (
	id INTEGER NOT NULL, 
	code VARCHAR(16) NOT NULL, 
	name VARCHAR(64) NOT NULL, is_active BOOLEAN DEFAULT 1 NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (code)
);
INSERT INTO "units_of_measure" VALUES(1,'m2','м²',1);
INSERT INTO "units_of_measure" VALUES(3,'m3','м³',1);
INSERT INTO "units_of_measure" VALUES(4,'pcs','шт.',1);
INSERT INTO "units_of_measure" VALUES(5,'vehicle','машина',1);
INSERT INTO "units_of_measure" VALUES(6,'hour','час',1);
INSERT INTO "units_of_measure" VALUES(7,'m2day','м²·день',1);
CREATE TABLE user_roles (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	role_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(role_id) REFERENCES roles (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	CONSTRAINT uq_user_roles_user_role UNIQUE (user_id, role_id)
);
INSERT INTO "user_roles" VALUES(1,1,1);
INSERT INTO "user_roles" VALUES(2,2,3);
INSERT INTO "user_roles" VALUES(3,3,4);
INSERT INTO "user_roles" VALUES(4,4,5);
CREATE TABLE user_warehouse_access (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	warehouse_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(warehouse_id) REFERENCES warehouses (id), 
	CONSTRAINT uq_user_warehouse_access UNIQUE (user_id, warehouse_id)
);
INSERT INTO "user_warehouse_access" VALUES(1,2,1);
INSERT INTO "user_warehouse_access" VALUES(2,2,2);
INSERT INTO "user_warehouse_access" VALUES(3,3,2);
INSERT INTO "user_warehouse_access" VALUES(4,4,2);
CREATE TABLE users (
	id INTEGER NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	full_name VARCHAR(255), 
	password_hash VARCHAR(255), 
	is_active BOOLEAN DEFAULT 1 NOT NULL, 
	is_admin BOOLEAN DEFAULT 0 NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (email)
);
INSERT INTO "users" VALUES(1,'admin@bsh-ru.ru','Администратор ПЛС','scrypt:32768:8:1$llJAtN8unDpDluTu$3ccb98ce4bb14fe8d7f83b5b1ebde3ab41ab73c8ce75ceec5ec0be4713a47974af2e67f70ee13d2acbe2b602790f53949815a4f971893c7a2cef5d461acb6483',1,1,'2026-09-02 04:33:31.868290','2026-09-02 04:33:31.868299');
INSERT INTO "users" VALUES(2,'transport@bsh-ru.ru','Транспортная логистика','scrypt:32768:8:1$ZLYIWrssRxxeDDwN$15e2db0cb0c0d965496561d8ebc0c90a1be343f9e6b9e0bfababff2a128bb96719a503c06cdfb922a05854e1d7d073d2342cb0c4b70c16e4bb02611e9135fca6',1,0,'2026-09-02 04:33:32.236837','2026-09-02 04:33:32.236848');
INSERT INTO "users" VALUES(3,'warehouse@bsh-ru.ru','Складская логистика','scrypt:32768:8:1$UUpmfiPNcEOQywLm$56da3aedb7f17a239eff3b22c9737b0fe335f39ca28994a989ab9616ee8e8e10ec0c8db7579058fb96282e162d4b03d07a7c5d3b8c9ec99e735093359d267b00',1,0,'2026-09-02 06:23:49.920752','2026-09-02 06:23:49.920759');
INSERT INTO "users" VALUES(4,'inventory@bsh-ru.ru','Управление запасами','scrypt:32768:8:1$7YmX3pM8xbGoqcFe$5fb3febb325f32f92931550ecc1d03fc8f283c378ce7931c6127c65583e34acb74170f0736c4130aff10b2ac7ffdc0848db1307f38d16631b6be04b22e945244',1,0,'2026-09-02 06:23:50.090936','2026-09-02 06:23:50.090941');
CREATE TABLE vehicle_operations (
	id INTEGER NOT NULL, 
	contract_id INTEGER NOT NULL, 
	warehouse_id INTEGER NOT NULL, 
	operation_date DATE NOT NULL, 
	plate_number VARCHAR(32), 
	volume_document_m3 NUMERIC(12, 3), 
	handling_type_code VARCHAR(32), 
	extra_handling_m3 NUMERIC(12, 3), 
	extra_document_set_qty INTEGER, 
	registered_at DATETIME, 
	departed_at DATETIME, 
	report_quantities JSON, 
	created_at DATETIME, operation_type_code VARCHAR(32), tractor_plate VARCHAR(64), trailer_plate VARCHAR(64), waybill_number VARCHAR(256), mx1_number VARCHAR(256), mx3_number VARCHAR(256), seal_number VARCHAR(128), torg2_number VARCHAR(128), vehicle_type_id INTEGER, source VARCHAR(32) DEFAULT 'manual' NOT NULL, security_request_id VARCHAR(64), 
	PRIMARY KEY (id), 
	FOREIGN KEY(contract_id) REFERENCES contracts (id), 
	FOREIGN KEY(warehouse_id) REFERENCES warehouses (id)
);
INSERT INTO "vehicle_operations" VALUES(1,1,1,'2026-08-15','А123ВС78',32.5,'manual',NULL,NULL,'2026-08-15 09:00:00.000000','2026-08-15 11:30:00.000000','{}','2026-09-02 04:33:32.341445',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(97,2,2,'2026-09-02','А000АА02',NULL,NULL,NULL,1,NULL,NULL,'{}','2026-09-02 07:56:38.061167','inbound','А000АА02',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'security','mock-client-0209-1');
INSERT INTO "vehicle_operations" VALUES(192,2,2,'2026-09-01','А000АА01',NULL,NULL,NULL,NULL,NULL,NULL,'{}','2026-09-02 08:52:08.267664','inbound','А000АА01',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'security','mock-client-0109-1');
INSERT INTO "vehicle_operations" VALUES(193,2,2,'2026-08-03','А613СС198',9.852,'manual',NULL,2,'2026-08-03 12:30:00.000000','2026-08-03 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 9.852, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.797119','outbound','А613СС198',NULL,'8008501729/8008502144',NULL,NULL,'30994868',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(194,2,2,'2026-08-03','218CS61/M7161',90.96,'mechanized',NULL,2,'2026-08-03 09:30:00.000000','2026-08-03 15:10:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 90.96, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.799939','inbound','218CS61','M7161','17056644',NULL,NULL,'0','56644',NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(195,2,2,'2026-08-03','В867УХ147/АР306047',69.344,'mechanized',NULL,2,'2026-08-03 14:00:00.000000','2026-08-03 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 69.344, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.801306','inbound','В867УХ147','АР306047','8008488528',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(196,2,2,'2026-08-03','Т375РР198/ЕА939978',67.33,'mechanized',NULL,2,'2026-08-03 13:00:00.000000','2026-08-03 15:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 67.33, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.802551','inbound','Т375РР198','ЕА939978','8008498730/8008502166/8008504757',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(197,2,2,'2026-08-03','219CS61/Z6481',71.953,'mechanized',NULL,2,'2026-08-03 12:30:00.000000','2026-08-03 16:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 71.953, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.804015','inbound','219CS61','Z6481','17056777',NULL,NULL,'0','56777',NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(198,2,2,'2026-08-04','К582ВЕ147/ВК298647',55.014,'mechanized',NULL,2,'2026-08-04 11:30:00.000000','2026-08-04 12:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 55.014, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.805481','inbound','К582ВЕ147','ВК298647','8008488531',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(199,2,2,'2026-08-04','В867УХ147/АР306047',69.284,'mechanized',NULL,2,'2026-08-04 12:30:00.000000','2026-08-04 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 69.284, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.806766','inbound','В867УХ147','АР306047','8008488530',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(200,2,2,'2026-08-04','К725ТХ126/СВ472726',26.237,'manual',NULL,2,'2026-08-04 13:30:00.000000','2026-08-04 15:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 26.237, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.808012','outbound','К725ТХ126','СВ472726','8008505170',NULL,NULL,'30994869',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(201,2,2,'2026-08-04','К526ЕК53/НК805453',68.625,'manual',NULL,2,'2026-08-04 13:00:00.000000','2026-08-04 16:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 68.625, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.809268','outbound','К526ЕК53','НК805453','8008505960',NULL,NULL,'30994863',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(202,2,2,'2026-08-05','О216МК198',11.783,'manual',NULL,2,'2026-08-05 09:30:00.000000','2026-08-05 10:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 11.783, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.810494','outbound','О216МК198',NULL,'8008505270/8008508258',NULL,NULL,'30994858',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(203,2,2,'2026-08-05','С156ТМ47',8.561,'manual',NULL,2,'2026-08-05 09:00:00.000000','2026-08-05 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 8.561, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.811726','outbound','С156ТМ47',NULL,'8008496265/8008501544/8008501548/8008502023/8008504415/8008508297',NULL,NULL,'30994855',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(204,2,2,'2026-08-05','О462ХР196/ВА173059',88.113,'manual',NULL,2,'2026-08-05 09:00:00.000000','2026-08-05 13:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 88.113, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.812973','outbound','О462ХР196','ВА173059','8008508594/8008508625/8008508626',NULL,NULL,'30994854',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(205,2,2,'2026-08-05','К810НО53/НМ010853',93.241,'manual',NULL,2,'2026-08-05 09:00:00.000000','2026-08-05 13:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 93.241, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.814261','outbound','К810НО53','НМ010853','8008506031/8008506032/8008506375',NULL,NULL,'30994859',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(206,2,2,'2026-08-05','М900РС163/АУ601163',18.76,'manual',NULL,2,'2026-08-05 13:00:00.000000','2026-08-05 15:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 18.76, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.815622','outbound','М900РС163','АУ601163','8008505351',NULL,NULL,'30994852',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(207,2,2,'2026-08-05','А954ОА134/ВТ603634',62.913,'manual',NULL,2,'2026-08-05 12:00:00.000000','2026-08-05 15:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 62.913, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.816875','outbound','А954ОА134','ВТ603634','8008494308/8008502285/8008505956',NULL,NULL,'30994857',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(208,2,2,'2026-08-06','С156ТМ47',0.579,'manual',NULL,2,'2026-08-06 09:00:00.000000','2026-08-06 10:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.579, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.818126','outbound','С156ТМ47',NULL,'8008508905',NULL,NULL,'30994888',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(209,2,2,'2026-08-06','О216МК198',8.246,'manual',NULL,2,'2026-08-06 09:00:00.000000','2026-08-06 10:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 8.246, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.819574','outbound','О216МК198',NULL,'8008509621/8008510944',NULL,NULL,'30994872',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(210,2,2,'2026-08-06','В867УХ147/АР306047',61.459,'mechanized',NULL,2,'2026-08-06 12:40:00.000000','2026-08-06 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 61.459, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.820887','inbound','В867УХ147','АР306047','8008488546',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(211,2,2,'2026-08-06','К106УР178',0.81,'mechanized',NULL,2,'2026-08-06 15:00:00.000000','2026-08-06 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.81, "elco_passports": 1}','2026-09-02 09:33:56.822113','outbound','К106УР178',NULL,'8008509141',NULL,NULL,'30994851',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(212,2,2,'2026-08-06','К582ВЕ147/ВК298647',62.429,'mechanized',NULL,2,'2026-08-06 14:30:00.000000','2026-08-06 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 62.429, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.823329','inbound','К582ВЕ147','ВК298647','8008488545',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(213,2,2,'2026-08-07','В867УХ147/АР306047',56.983,'mechanized',NULL,2,'2026-08-07 09:00:00.000000','2026-08-07 10:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 56.983, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.824586','inbound','В867УХ147','АР306047','8008488535/8008513662',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(214,2,2,'2026-08-07','У848МО761/СН339161',31.717,'manual',NULL,2,'2026-08-07 09:00:00.000000','2026-08-07 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 31.717, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.825845','outbound','У848МО761','СН339161','8008511318',NULL,NULL,'30994844',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(215,2,2,'2026-08-07','Т375РР198/ЕА939978',65.173,'mechanized',NULL,1,'2026-08-07 13:00:00.000000','2026-08-07 14:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 65.173, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.827032','inbound','Т375РР198','ЕА939978','8008488542',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(216,2,2,'2026-08-07','О216МК198',0.633,'manual',NULL,1,'2026-08-07 14:00:00.000000','2026-08-07 15:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.633, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.828225','outbound','О216МК198',NULL,'8008510761/8008513470',NULL,NULL,'30994849',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(217,2,2,'2026-08-07','BB17427/A5315I7',51.5,'manual',NULL,1,'2026-08-07 11:30:00.000000','2026-08-07 16:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 51.5, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.829418','outbound','BB17427','A5315I7','8008510641/8008510647/8008510653/8008513120/8008513131/8008513466',NULL,NULL,'30994845',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(218,2,2,'2026-08-10','Р552ВО198',39.384,'manual',NULL,1,'2026-08-10 09:40:00.000000','2026-08-10 11:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 39.384, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.830594','outbound','Р552ВО198',NULL,'8008514702/8008515608',NULL,NULL,'30994846',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(219,2,2,'2026-08-10','В867УХ147/АР306047',46.072,'mechanized',NULL,1,'2026-08-10 12:00:00.000000','2026-08-10 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 46.072, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.831781','inbound','В867УХ147','АР306047','8008480507/8008516142',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(220,2,2,'2026-08-10','А444СН36/ВЕ038936',58.283,'manual',NULL,1,'2026-08-10 11:30:00.000000','2026-08-10 14:30:00.000000','{"inbound_manual_m3": 58.283, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.832950','outbound','А444СН36','ВЕ038936','8008515545/8008515929',NULL,NULL,'30994842',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(221,2,2,'2026-08-10','B713CT134/ЕА230834',56.205,'manual',NULL,1,'2026-08-10 12:00:00.000000','2026-08-10 15:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 56.205, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.834261','outbound','B713CT134','ЕА230834','8008501500/8008509617/8008514288/8008514392/8008514680',NULL,NULL,'30994833',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(222,2,2,'2026-08-10','К106УР178',0.81,'mechanized',NULL,1,'2026-08-10 13:30:00.000000','2026-08-10 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.81, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.835658','inbound','К106УР178',NULL,'84938085',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(223,2,2,'2026-08-11','C010OK198/ЕЕ043778',70.226,'manual',NULL,1,'2026-08-11 09:30:00.000000','2026-08-11 13:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 70.226, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.836900','outbound','C010OK198','ЕЕ043778','8008516713/8008518354',NULL,NULL,'30994834',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(224,2,2,'2026-08-11','В867УХ147/АР306047',66.355,'manual',NULL,1,'2026-08-11 12:00:00.000000','2026-08-11 14:30:00.000000','{"inbound_manual_m3": 66.355, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.838151','inbound','В867УХ147','АР306047','8008517796',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(225,2,2,'2026-08-11','АС6427-1  MI590YI',88.56,'manual',NULL,1,'2026-08-11 09:00:00.000000','2026-08-11 15:00:00.000000','{"inbound_manual_m3": 88.56, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.839380','inbound','АС6427-1  MI590YI',NULL,'17058956',NULL,NULL,'0','58956',NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(226,2,2,'2026-08-12','Т375РР198/ЕА939978',66.912,'manual',NULL,1,'2026-08-12 09:00:00.000000','2026-08-12 11:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 66.912, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.840642','outbound','Т375РР198','ЕА939978','8008520547/8008520551/8008520554/8008520788/8008520874',NULL,NULL,'30994836',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(227,2,2,'2026-08-12','219CS61/T7116',91.91,'mechanized',NULL,1,'2026-08-12 09:00:00.000000','2026-08-12 13:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 91.91, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.841872','inbound','219CS61','T7116','17059305',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(228,2,2,'2026-08-12','М738ТА716/ВС041016',94.151,'mechanized',NULL,1,'2026-08-12 09:00:00.000000','2026-08-12 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 94.151, "elco_passports": 1}','2026-09-02 09:33:56.843118','outbound','М738ТА716','ВС041016','8008520789/8008520790/8008520932',NULL,NULL,'30994835',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(229,2,2,'2026-08-12','В867УХ147/АР306047',60.515,'mechanized',NULL,1,'2026-08-12 12:30:00.000000','2026-08-12 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 60.515, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.844383','inbound','В867УХ147','АР306047','8008519004',NULL,NULL,'0','519004',NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(230,2,2,'2026-08-12','Р548УХ198/ВТ413078',69.57,'mechanized',NULL,1,'2026-08-12 12:30:00.000000','2026-08-12 14:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 69.57, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.845712','inbound','Р548УХ198','ВТ413078','8008421443',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(231,2,2,'2026-08-13','Н202РМ198',4.901,'manual',NULL,1,'2026-08-13 09:00:00.000000','2026-08-13 10:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 4.901, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.846958','outbound','Н202РМ198',NULL,'8008521320',NULL,NULL,'30994831',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(232,2,2,'2026-08-13','Т375РР198/ЕА939978',60.399,'manual',NULL,1,'2026-08-13 12:30:00.000000','2026-08-13 14:30:00.000000','{"inbound_manual_m3": 60.399, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.848207','inbound','Т375РР198','ЕА939978','8008519006',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(233,2,2,'2026-08-13','В867УХ147/АР306047',61.494,'mechanized',NULL,1,'2026-08-13 12:30:00.000000','2026-08-13 14:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 61.494, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.849608','inbound','В867УХ147','АР306047','8008519007/8008523521',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(234,2,2,'2026-08-13','АВ90091/1TL5671',87,'mechanized',NULL,1,'2026-08-13 09:00:00.000000','2026-08-13 14:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 87.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.850922','inbound','АВ90091','1TL5671','17057008',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(235,2,2,'2026-08-13','Т131СЕ178',14.478,'manual',NULL,1,'2026-08-13 15:00:00.000000','2026-08-13 16:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 14.478, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.852181','outbound','Т131СЕ178',NULL,'8008518227/8008519145/8008520302/8008521255/8008521261/8008521269/8008523526',NULL,NULL,'30994861',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(236,2,2,'2026-08-14','В171ВУ178/АН754647',60.36,'manual',NULL,1,'2026-08-14 09:30:00.000000','2026-08-14 11:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 60.36, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.853416','outbound','В171ВУ178','АН754647','8008524305/8008524310/8008524383/8008525699/8008526341/8008526595',NULL,NULL,'30994814',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(237,2,2,'2026-08-14','В867УХ147/АР306047',51.976,'manual',NULL,1,'2026-08-14 13:10:00.000000','2026-08-14 14:20:00.000000','{"inbound_manual_m3": 51.976, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.854732','inbound','В867УХ147','АР306047','8008524127',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(238,2,2,'2026-08-14','К582ВЕ147/ВК298647',50.309,'manual',NULL,1,'2026-08-14 12:00:00.000000','2026-08-14 14:30:00.000000','{"inbound_manual_m3": 50.309, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.856030','inbound','К582ВЕ147','ВК298647','8008519012/8008525798',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(239,2,2,'2026-08-17','Н202РМ198',10.546,'mechanized',NULL,1,'2026-08-17 09:30:00.000000','2026-08-17 10:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 10.546, "elco_passports": 1}','2026-09-02 09:33:56.857345','outbound','Н202РМ198',NULL,'8008520542/8008521306',NULL,NULL,'30994829',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(240,2,2,'2026-08-17','С156ТМ47',3.437,'manual',NULL,1,'2026-08-17 10:00:00.000000','2026-08-17 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 3.437, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.858591','outbound','С156ТМ47',NULL,'8008526383/8008526388/8008527817',NULL,NULL,'30994818',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(241,2,2,'2026-08-17','Н349НК26/СВ517126',71.25,'manual',NULL,1,'2026-08-17 13:30:00.000000','2026-08-17 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 71.25, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.859822','outbound','Н349НК26','СВ517126','8008527673/8008527698',NULL,NULL,'30994830',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(242,2,2,'2026-08-17','В867УХ147/АР306047',70.051,'manual',NULL,1,'2026-08-17 13:30:00.000000','2026-08-17 16:30:00.000000','{"inbound_manual_m3": 70.051, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.861081','inbound','В867УХ147','АР306047','8008524218/8008527777',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(243,2,2,'2026-08-17','М612ТН797/ТВ707477',78.613,'manual',NULL,1,'2026-08-17 15:30:00.000000','2026-08-17 17:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 78.613, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.862319','outbound','М612ТН797','ТВ707477','8008521887 8008525793 8008525795',NULL,'8008521887/8008525793/8008525795','30994811',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(244,2,2,'2026-08-18','М952РК161/СА429661',70.89,'mechanized',NULL,1,'2026-08-18 10:00:00.000000','2026-08-18 12:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 70.89, "elco_passports": 1}','2026-09-02 09:33:56.863551','outbound','М952РК161','СА429661','8008529845/8008529847',NULL,NULL,'30994826',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(245,2,2,'2026-08-18','Р552ВО198',4.479,'manual',NULL,1,'2026-08-18 15:00:00.000000','2026-08-18 16:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 4.479, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.865104','outbound','Р552ВО198',NULL,'8008530107/8008530200',NULL,NULL,'30994816',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(246,2,2,'2026-08-19','С156ТМ47',40.742,'manual',NULL,1,'2026-08-19 10:00:00.000000','2026-08-19 13:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 40.742, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.866435','outbound','С156ТМ47',NULL,'8008532548/8008532588/8008533158/8008533349',NULL,NULL,'30994813',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(247,2,2,'2026-08-19','К838КС53/НК135253',92.704,'manual',NULL,1,'2026-08-19 10:40:00.000000','2026-08-19 14:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 92.704, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.867705','outbound','К838КС53','НК135253','8008533375/8008533376',NULL,NULL,'30994817',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(248,2,2,'2026-08-19','С156ТМ47',2.033,'manual',NULL,1,'2026-08-19 14:40:00.000000','2026-08-19 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 2.033, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.868956','outbound','С156ТМ47',NULL,'8008532643/8008532887',NULL,NULL,'30994911',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(249,2,2,'2026-08-19','В867УХ147/АР306047',61.639,'mechanized',NULL,1,'2026-08-19 14:00:00.000000','2026-08-19 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 61.639, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.870233','inbound','В867УХ147','АР306047','8008533211',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(250,2,2,'2026-08-19','К582ВЕ147/ВК298647',45.72,'manual',NULL,1,'2026-08-19 09:00:00.000000','2026-08-19 10:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 45.72, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.871479','outbound','К582ВЕ147','ВК298647','8008533089/8008533160',NULL,NULL,'30994812',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(251,2,2,'2026-08-19','AT34157/A5788E7',69.085,'mechanized',NULL,1,'2026-08-19 10:40:00.000000','2026-08-19 16:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 69.085, "elco_passports": 1}','2026-09-02 09:33:56.872717','outbound','AT34157','A5788E7','8008529862/8008530578',NULL,NULL,'30994920/30994919',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(252,2,2,'2026-08-20','С156ТМ47',14.251,'manual',NULL,1,'2026-08-20 09:20:00.000000','2026-08-20 13:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 14.251, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.873971','outbound','С156ТМ47',NULL,'8008535368/8008535468/8008535487/8008535525/8008535994',NULL,'8008529892/8008533228/8008534371/8008534377','30994806',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(253,2,2,'2026-08-20','О449НТ797/УХ953177',82.013,'manual',NULL,1,'2026-08-20 09:00:00.000000','2026-08-20 13:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 82.013, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.875443','outbound','О449НТ797','УХ953177','8008530185/8008530191/8008533023/8008536066',NULL,NULL,'30994827',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(254,2,2,'2026-08-20','В825УУ47/АТ730447',89.463,'manual',NULL,1,'2026-08-20 09:00:00.000000','2026-08-20 14:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 89.463, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.876714','outbound','В825УУ47','АТ730447','8008529892/8008533228/8008534371/8008534377',NULL,NULL,'30994810/30994809',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(255,2,2,'2026-08-20','О955ХМ161/СВ840261',71.449,'manual',NULL,1,'2026-08-20 12:20:00.000000','2026-08-20 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 71.449, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.877960','outbound','О955ХМ161','СВ840261','8008536113/8008536115/8008536127',NULL,NULL,'30994823',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(256,2,2,'2026-08-20','В306ОВ178/ВВ472447',75.213,'manual',NULL,1,'2026-08-20 10:30:00.000000','2026-08-20 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 75.213, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.879484','outbound','В306ОВ178','ВВ472447','8008531158/8008531210/8008532636/8008533110/8008533910',NULL,NULL,'30994803',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(257,2,2,'2026-08-21','С156ТМ47',4.542,'manual',NULL,1,'2026-08-21 11:30:00.000000','2026-08-21 12:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 4.542, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.880834','outbound','С156ТМ47',NULL,'8008536767/8008537643/8008538175/8008538640',NULL,NULL,'30994808',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(258,2,2,'2026-08-21','К582ВЕ147/ВК298647',55.033,'mechanized',NULL,1,'2026-08-21 11:57:00.000000','2026-08-21 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 55.033, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.882098','inbound','К582ВЕ147','ВК298647','8008538166',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(259,2,2,'2026-08-21','Н202РМ198',10.53,'manual',NULL,1,'2026-08-21 12:50:00.000000','2026-08-21 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 10.53, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 09:33:56.883327','outbound','Н202РМ198',NULL,'8008442881/8008527327',NULL,NULL,'30994801',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(260,2,2,'2026-08-24','Р552ВО198',8.078,'manual',NULL,1,'2026-08-24 09:40:00.000000','2026-08-24 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 8.078, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.884644','outbound','Р552ВО198',NULL,'8008469261',NULL,NULL,'30994805',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(261,2,2,'2026-08-24','Р088ММ40/АМ102540',94.299,'manual',NULL,1,'2026-08-24 12:00:00.000000','2026-08-24 17:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 94.299, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.885943','outbound','Р088ММ40','АМ102540','8008540931/8008540932',NULL,NULL,'30994802',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(262,2,2,'2026-08-25','С156ТМ47',9.397,'manual',NULL,1,'2026-08-25 09:00:00.000000','2026-08-25 10:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 9.397, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.887195','outbound','С156ТМ47',NULL,'8008543131/8008543898/8008543909',NULL,NULL,'30994804',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(263,2,2,'2026-08-25','О216МК198',8.13,'manual',NULL,1,'2026-08-25 09:40:00.000000','2026-08-25 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 8.13, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.888419','outbound','О216МК198',NULL,'8008540875/8008542792/8008543064/8008543258',NULL,NULL,'30994828',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(264,2,2,'2026-08-25','Т207НЕ178',5.486,'manual',NULL,1,'2026-08-25 09:50:00.000000','2026-08-25 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 5.486, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.889655','outbound','Т207НЕ178',NULL,'8008532930/8008532964',NULL,NULL,'30994822',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(265,2,2,'2026-08-25','М616УО196/АУ819966',37.748,'manual',NULL,1,'2026-08-25 09:10:00.000000','2026-08-25 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 37.748, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.890914','outbound','М616УО196','АУ819966','8008543768',NULL,NULL,'30994807',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(266,2,2,'2026-08-25','М338СМ761/СУ153561',33.81,'manual',NULL,1,'2026-08-25 09:50:00.000000','2026-08-25 12:15:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 33.81, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.892182','outbound','М338СМ761','СУ153561','8008543544',NULL,NULL,'30994825',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(267,2,2,'2026-08-25','К582ВЕ147/ВК298647',50.382,'manual',NULL,1,'2026-08-25 12:03:00.000000','2026-08-25 13:30:00.000000','{"inbound_manual_m3": 50.382, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.893431','inbound','К582ВЕ147','ВК298647','8008540882/8008543828','8008531120/8008531149/8008531166',NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(268,2,2,'2026-08-25','Р452ОО62/АМ039662',105.552,'mechanized',NULL,1,'2026-08-25 12:30:00.000000','2026-08-25 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 52.776, "inbound_mech_m3": 0.0, "outbound_mech_m3": 52.776}','2026-09-02 09:33:56.894763','outbound','Р452ОО62','АМ039662','8008531120/8008531149/8008531166','-',NULL,'30994754',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(269,2,2,'2026-08-25','Р028ОН32',7.723,'manual',NULL,1,'2026-08-25 14:50:00.000000','2026-08-25 16:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 7.723, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.898022','outbound','Р028ОН32',NULL,'8008469244',NULL,NULL,'30994757',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(270,2,2,'2026-08-26','К574НЕ147',0.637,'manual',NULL,1,'2026-08-26 09:00:00.000000','2026-08-26 10:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.637, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.899302','outbound','К574НЕ147',NULL,'8008545002/8008546424',NULL,NULL,'30994756',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(271,2,2,'2026-08-26','К582ВЕ147/ВК298647',68.668,'manual',NULL,1,'2026-08-26 09:00:00.000000','2026-08-26 11:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 68.668, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.900536','outbound','К582ВЕ147','ВК298647','8008547242/8008547248',NULL,NULL,'30994780',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(272,2,2,'2026-08-26','О506УУ40/ВН237516',92.683,'manual',NULL,1,'2026-08-26 10:10:00.000000','2026-08-26 14:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 92.683, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.901762','outbound','О506УУ40','ВН237516','8008547163',NULL,NULL,'30994741',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(273,2,2,'2026-08-27','C156ТМ147',4.092,'manual',NULL,1,'2026-08-27 09:00:00.000000','2026-08-27 10:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 4.092, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.902984','outbound','C156ТМ147',NULL,'8008547052/8008547155/8008550526',NULL,NULL,'30994743',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(274,2,2,'2026-08-27','К582ВЕ147/ВК298647',55.614,'manual',NULL,1,'2026-08-27 09:00:00.000000','2026-08-27 10:30:00.000000','{"inbound_manual_m3": 55.614, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.904278','inbound','К582ВЕ147','ВК298647','8008550754/8008550805',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(275,2,2,'2026-08-27','К106УР178',3.979,'manual',NULL,1,'2026-08-27 12:30:00.000000','2026-08-27 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 3.979, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.905619','outbound','К106УР178',NULL,'8008547986/8008548011',NULL,NULL,'30994769',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(276,2,2,'2026-08-28','М256ОК763/ВР823363',21.548,'manual',NULL,1,'2026-08-28 09:00:00.000000','2026-08-28 11:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 21.548, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.906900','outbound','М256ОК763','ВР823363','8008550492',NULL,NULL,'30994770',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(277,2,2,'2026-08-28','В171ВУ178/АН754647',65.559,'manual',NULL,1,'2026-08-28 09:10:00.000000','2026-08-28 12:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 65.559, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.908217','outbound','В171ВУ178','АН754647','8008552215/8008552247/8008553573/8008553576/8008554471',NULL,NULL,'30994744',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(278,2,2,'2026-08-28','Т295АМ39',32.649,'manual',NULL,1,'2026-08-28 14:30:00.000000','2026-08-28 17:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 32.649, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.909445','outbound','Т295АМ39',NULL,'8008540620/8008540659/8008540668/8008552511',NULL,NULL,'30994763',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(279,2,2,'2026-08-31','Р552ВО198',27.377,'manual',NULL,1,'2026-08-31 09:00:00.000000','2026-08-31 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 27.377, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.910919','outbound','Р552ВО198',NULL,'8008550297',NULL,NULL,'30994755',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(280,2,2,'2026-08-31','К941АС53',7.056,'manual',NULL,1,'2026-08-31 09:00:00.000000','2026-08-31 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 7.056, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.945845','outbound','К941АС53',NULL,'8008544629/8008547193/8008547232/8008548428/8008554022/8008557482',NULL,NULL,'30994748',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(281,2,2,'2026-08-31','218CS61/K7161',62.342,'mechanized',NULL,1,'2026-08-31 12:30:00.000000','2026-08-31 16:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 62.342, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.952003','inbound','218CS61','K7161','17061862',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(282,2,2,'2026-08-31','AX30067/A8100E7',57.328,'manual',NULL,1,'2026-08-31 10:00:00.000000','2026-08-31 15:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 57.328, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.955757','outbound','AX30067','A8100E7','8008546706/8008554791/8008555281/8008555779',NULL,NULL,'30994751/30994752',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(283,2,2,'2026-08-31','M853CE26/ЕА510926',69.043,'manual',NULL,1,'2026-08-31 12:20:00.000000','2026-08-31 15:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 69.043, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.957732','outbound','M853CE26','ЕА510926','8008555971/8008555983/8008557797',NULL,NULL,'30994749',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(284,2,2,'2026-08-31','О216МК198',6.48,'manual',NULL,1,'2026-08-31 12:50:00.000000','2026-08-31 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 6.48, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.959659','outbound','О216МК198',NULL,'8008554736',NULL,NULL,'30994774',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(285,2,2,'2026-08-31','Х676ЕХ797/УХ117377',54.5,'manual',NULL,1,'2026-08-31 12:30:00.000000','2026-08-31 16:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 54.5, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.961210','outbound','Х676ЕХ797','УХ117377','8008552221/8008554476/8008554481/8008554488/8008554492/8008555469/8008555972',NULL,NULL,'30994766',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(286,2,2,'2026-08-31','С480НС67/74AEG10',66.374,'manual',NULL,1,'2026-08-31 13:10:00.000000','2026-08-31 17:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 66.374, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 09:33:56.962737','outbound','С480НС67','74AEG10','8008543546',NULL,NULL,'30994768',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(381,2,2,'2026-09-02','В111ВВ02',NULL,NULL,NULL,NULL,NULL,NULL,'{}','2026-09-02 12:55:13.902927','inbound','В111ВВ02',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'security','mock-client-0209-2');
INSERT INTO "vehicle_operations" VALUES(476,2,2,'2026-09-01','В111ВВ01',NULL,NULL,NULL,NULL,NULL,NULL,'{}','2026-09-02 13:40:57.046075','inbound','В111ВВ01',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'security','mock-client-0109-2');
INSERT INTO "vehicle_operations" VALUES(477,2,2,'2026-08-31','А000АА31',NULL,NULL,NULL,NULL,NULL,NULL,'{}','2026-09-02 13:41:09.026358','inbound','А000АА31',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'security','mock-client-3108-1');
INSERT INTO "vehicle_operations" VALUES(478,2,2,'2026-08-31','В111ВВ31',NULL,NULL,NULL,NULL,NULL,NULL,'{}','2026-09-02 13:41:09.028636','inbound','В111ВВ31',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'security','mock-client-3108-2');
INSERT INTO "vehicle_operations" VALUES(479,2,2,'2026-08-03','А613СС198',9.852,'manual',NULL,2,'2026-08-03 12:30:00.000000','2026-08-03 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 9.852, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.117200','outbound','А613СС198',NULL,'8008501729/8008502144',NULL,NULL,'30994868',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(480,2,2,'2026-08-03','218CS61/M7161',90.96,'mechanized',NULL,2,'2026-08-03 09:30:00.000000','2026-08-03 15:10:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 90.96, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.122330','inbound','218CS61','M7161','17056644',NULL,NULL,'0','56644',NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(481,2,2,'2026-08-03','В867УХ147/АР306047',69.344,'mechanized',NULL,2,'2026-08-03 14:00:00.000000','2026-08-03 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 69.344, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.124149','inbound','В867УХ147','АР306047','8008488528',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(482,2,2,'2026-08-03','Т375РР198/ЕА939978',67.33,'mechanized',NULL,2,'2026-08-03 13:00:00.000000','2026-08-03 15:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 67.33, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.125746','inbound','Т375РР198','ЕА939978','8008498730/8008502166/8008504757',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(483,2,2,'2026-08-03','219CS61/Z6481',71.953,'mechanized',NULL,2,'2026-08-03 12:30:00.000000','2026-08-03 16:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 71.953, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.127668','inbound','219CS61','Z6481','17056777',NULL,NULL,'0','56777',NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(484,2,2,'2026-08-04','К582ВЕ147/ВК298647',55.014,'mechanized',NULL,2,'2026-08-04 11:30:00.000000','2026-08-04 12:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 55.014, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.131998','inbound','К582ВЕ147','ВК298647','8008488531',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(485,2,2,'2026-08-04','В867УХ147/АР306047',69.284,'mechanized',NULL,2,'2026-08-04 12:30:00.000000','2026-08-04 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 69.284, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.134323','inbound','В867УХ147','АР306047','8008488530',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(486,2,2,'2026-08-04','К725ТХ126/СВ472726',26.237,'manual',NULL,2,'2026-08-04 13:30:00.000000','2026-08-04 15:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 26.237, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.136770','outbound','К725ТХ126','СВ472726','8008505170',NULL,NULL,'30994869',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(487,2,2,'2026-08-04','К526ЕК53/НК805453',68.625,'manual',NULL,2,'2026-08-04 13:00:00.000000','2026-08-04 16:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 68.625, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.138498','outbound','К526ЕК53','НК805453','8008505960',NULL,NULL,'30994863',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(488,2,2,'2026-08-05','О216МК198',11.783,'manual',NULL,2,'2026-08-05 09:30:00.000000','2026-08-05 10:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 11.783, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.140098','outbound','О216МК198',NULL,'8008505270/8008508258',NULL,NULL,'30994858',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(489,2,2,'2026-08-05','С156ТМ47',8.561,'manual',NULL,2,'2026-08-05 09:00:00.000000','2026-08-05 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 8.561, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.141682','outbound','С156ТМ47',NULL,'8008496265/8008501544/8008501548/8008502023/8008504415/8008508297',NULL,NULL,'30994855',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(490,2,2,'2026-08-05','О462ХР196/ВА173059',88.113,'manual',NULL,2,'2026-08-05 09:00:00.000000','2026-08-05 13:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 88.113, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.143580','outbound','О462ХР196','ВА173059','8008508594/8008508625/8008508626',NULL,NULL,'30994854',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(491,2,2,'2026-08-05','К810НО53/НМ010853',93.241,'manual',NULL,2,'2026-08-05 09:00:00.000000','2026-08-05 13:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 93.241, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.145193','outbound','К810НО53','НМ010853','8008506031/8008506032/8008506375',NULL,NULL,'30994859',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(492,2,2,'2026-08-05','М900РС163/АУ601163',18.76,'manual',NULL,2,'2026-08-05 13:00:00.000000','2026-08-05 15:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 18.76, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.149185','outbound','М900РС163','АУ601163','8008505351',NULL,NULL,'30994852',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(493,2,2,'2026-08-05','А954ОА134/ВТ603634',62.913,'manual',NULL,2,'2026-08-05 12:00:00.000000','2026-08-05 15:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 62.913, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.152503','outbound','А954ОА134','ВТ603634','8008494308/8008502285/8008505956',NULL,NULL,'30994857',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(494,2,2,'2026-08-06','С156ТМ47',0.579,'manual',NULL,2,'2026-08-06 09:00:00.000000','2026-08-06 10:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.579, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.154405','outbound','С156ТМ47',NULL,'8008508905',NULL,NULL,'30994888',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(495,2,2,'2026-08-06','О216МК198',8.246,'manual',NULL,2,'2026-08-06 09:00:00.000000','2026-08-06 10:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 8.246, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.156126','outbound','О216МК198',NULL,'8008509621/8008510944',NULL,NULL,'30994872',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(496,2,2,'2026-08-06','В867УХ147/АР306047',61.459,'mechanized',NULL,2,'2026-08-06 12:40:00.000000','2026-08-06 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 61.459, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.157784','inbound','В867УХ147','АР306047','8008488546',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(497,2,2,'2026-08-06','К106УР178',0.81,'mechanized',NULL,2,'2026-08-06 15:00:00.000000','2026-08-06 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.81, "elco_passports": 1}','2026-09-02 13:45:29.159772','outbound','К106УР178',NULL,'8008509141',NULL,NULL,'30994851',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(498,2,2,'2026-08-06','К582ВЕ147/ВК298647',62.429,'mechanized',NULL,2,'2026-08-06 14:30:00.000000','2026-08-06 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 62.429, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.161513','inbound','К582ВЕ147','ВК298647','8008488545',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(499,2,2,'2026-08-07','В867УХ147/АР306047',56.983,'mechanized',NULL,2,'2026-08-07 09:00:00.000000','2026-08-07 10:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 56.983, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.165721','inbound','В867УХ147','АР306047','8008488535/8008513662',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(500,2,2,'2026-08-07','У848МО761/СН339161',31.717,'manual',NULL,2,'2026-08-07 09:00:00.000000','2026-08-07 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 31.717, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.168948','outbound','У848МО761','СН339161','8008511318',NULL,NULL,'30994844',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(501,2,2,'2026-08-07','Т375РР198/ЕА939978',65.173,'mechanized',NULL,1,'2026-08-07 13:00:00.000000','2026-08-07 14:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 65.173, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.170577','inbound','Т375РР198','ЕА939978','8008488542',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(502,2,2,'2026-08-07','О216МК198',0.633,'manual',NULL,1,'2026-08-07 14:00:00.000000','2026-08-07 15:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.633, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.172079','outbound','О216МК198',NULL,'8008510761/8008513470',NULL,NULL,'30994849',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(503,2,2,'2026-08-07','BB17427/A5315I7',51.5,'manual',NULL,1,'2026-08-07 11:30:00.000000','2026-08-07 16:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 51.5, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.173587','outbound','BB17427','A5315I7','8008510641/8008510647/8008510653/8008513120/8008513131/8008513466',NULL,NULL,'30994845',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(504,2,2,'2026-08-10','Р552ВО198',39.384,'manual',NULL,1,'2026-08-10 09:40:00.000000','2026-08-10 11:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 39.384, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.175412','outbound','Р552ВО198',NULL,'8008514702/8008515608',NULL,NULL,'30994846',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(505,2,2,'2026-08-10','В867УХ147/АР306047',46.072,'mechanized',NULL,1,'2026-08-10 12:00:00.000000','2026-08-10 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 46.072, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.177019','inbound','В867УХ147','АР306047','8008480507/8008516142',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(506,2,2,'2026-08-10','А444СН36/ВЕ038936',58.283,'manual',NULL,1,'2026-08-10 11:30:00.000000','2026-08-10 14:30:00.000000','{"inbound_manual_m3": 58.283, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.178530','outbound','А444СН36','ВЕ038936','8008515545/8008515929',NULL,NULL,'30994842',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(507,2,2,'2026-08-10','B713CT134/ЕА230834',56.205,'manual',NULL,1,'2026-08-10 12:00:00.000000','2026-08-10 15:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 56.205, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.183801','outbound','B713CT134','ЕА230834','8008501500/8008509617/8008514288/8008514392/8008514680',NULL,NULL,'30994833',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(508,2,2,'2026-08-10','К106УР178',0.81,'mechanized',NULL,1,'2026-08-10 13:30:00.000000','2026-08-10 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.81, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.185621','inbound','К106УР178',NULL,'84938085',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(509,2,2,'2026-08-11','C010OK198/ЕЕ043778',70.226,'manual',NULL,1,'2026-08-11 09:30:00.000000','2026-08-11 13:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 70.226, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.187132','outbound','C010OK198','ЕЕ043778','8008516713/8008518354',NULL,NULL,'30994834',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(510,2,2,'2026-08-11','В867УХ147/АР306047',66.355,'manual',NULL,1,'2026-08-11 12:00:00.000000','2026-08-11 14:30:00.000000','{"inbound_manual_m3": 66.355, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.188673','inbound','В867УХ147','АР306047','8008517796',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(511,2,2,'2026-08-11','АС6427-1  MI590YI',88.56,'manual',NULL,1,'2026-08-11 09:00:00.000000','2026-08-11 15:00:00.000000','{"inbound_manual_m3": 88.56, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.190146','inbound','АС6427-1  MI590YI',NULL,'17058956',NULL,NULL,'0','58956',NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(512,2,2,'2026-08-12','Т375РР198/ЕА939978',66.912,'manual',NULL,1,'2026-08-12 09:00:00.000000','2026-08-12 11:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 66.912, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.192280','outbound','Т375РР198','ЕА939978','8008520547/8008520551/8008520554/8008520788/8008520874',NULL,NULL,'30994836',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(513,2,2,'2026-08-12','219CS61/T7116',91.91,'mechanized',NULL,1,'2026-08-12 09:00:00.000000','2026-08-12 13:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 91.91, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.194016','inbound','219CS61','T7116','17059305',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(514,2,2,'2026-08-12','М738ТА716/ВС041016',94.151,'mechanized',NULL,1,'2026-08-12 09:00:00.000000','2026-08-12 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 94.151, "elco_passports": 1}','2026-09-02 13:45:29.195854','outbound','М738ТА716','ВС041016','8008520789/8008520790/8008520932',NULL,NULL,'30994835',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(515,2,2,'2026-08-12','В867УХ147/АР306047',60.515,'mechanized',NULL,1,'2026-08-12 12:30:00.000000','2026-08-12 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 60.515, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.201173','inbound','В867УХ147','АР306047','8008519004',NULL,NULL,'0','519004',NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(516,2,2,'2026-08-12','Р548УХ198/ВТ413078',69.57,'mechanized',NULL,1,'2026-08-12 12:30:00.000000','2026-08-12 14:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 69.57, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.203060','inbound','Р548УХ198','ВТ413078','8008421443',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(517,2,2,'2026-08-13','Н202РМ198',4.901,'manual',NULL,1,'2026-08-13 09:00:00.000000','2026-08-13 10:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 4.901, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.204892','outbound','Н202РМ198',NULL,'8008521320',NULL,NULL,'30994831',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(518,2,2,'2026-08-13','Т375РР198/ЕА939978',60.399,'manual',NULL,1,'2026-08-13 12:30:00.000000','2026-08-13 14:30:00.000000','{"inbound_manual_m3": 60.399, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.206655','inbound','Т375РР198','ЕА939978','8008519006',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(519,2,2,'2026-08-13','В867УХ147/АР306047',61.494,'mechanized',NULL,1,'2026-08-13 12:30:00.000000','2026-08-13 14:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 61.494, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.208347','inbound','В867УХ147','АР306047','8008519007/8008523521',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(520,2,2,'2026-08-13','АВ90091/1TL5671',87,'mechanized',NULL,1,'2026-08-13 09:00:00.000000','2026-08-13 14:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 87.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.209996','inbound','АВ90091','1TL5671','17057008',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(521,2,2,'2026-08-13','Т131СЕ178',14.478,'manual',NULL,1,'2026-08-13 15:00:00.000000','2026-08-13 16:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 14.478, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.211924','outbound','Т131СЕ178',NULL,'8008518227/8008519145/8008520302/8008521255/8008521261/8008521269/8008523526',NULL,NULL,'30994861',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(522,2,2,'2026-08-14','В171ВУ178/АН754647',60.36,'manual',NULL,1,'2026-08-14 09:30:00.000000','2026-08-14 11:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 60.36, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.217617','outbound','В171ВУ178','АН754647','8008524305/8008524310/8008524383/8008525699/8008526341/8008526595',NULL,NULL,'30994814',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(523,2,2,'2026-08-14','В867УХ147/АР306047',51.976,'manual',NULL,1,'2026-08-14 13:10:00.000000','2026-08-14 14:20:00.000000','{"inbound_manual_m3": 51.976, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.219423','inbound','В867УХ147','АР306047','8008524127',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(524,2,2,'2026-08-14','К582ВЕ147/ВК298647',50.309,'manual',NULL,1,'2026-08-14 12:00:00.000000','2026-08-14 14:30:00.000000','{"inbound_manual_m3": 50.309, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.221287','inbound','К582ВЕ147','ВК298647','8008519012/8008525798',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(525,2,2,'2026-08-17','Н202РМ198',10.546,'mechanized',NULL,1,'2026-08-17 09:30:00.000000','2026-08-17 10:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 10.546, "elco_passports": 1}','2026-09-02 13:45:29.222965','outbound','Н202РМ198',NULL,'8008520542/8008521306',NULL,NULL,'30994829',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(526,2,2,'2026-08-17','С156ТМ47',3.437,'manual',NULL,1,'2026-08-17 10:00:00.000000','2026-08-17 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 3.437, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.224554','outbound','С156ТМ47',NULL,'8008526383/8008526388/8008527817',NULL,NULL,'30994818',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(527,2,2,'2026-08-17','Н349НК26/СВ517126',71.25,'manual',NULL,1,'2026-08-17 13:30:00.000000','2026-08-17 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 71.25, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.226094','outbound','Н349НК26','СВ517126','8008527673/8008527698',NULL,NULL,'30994830',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(528,2,2,'2026-08-17','В867УХ147/АР306047',70.051,'manual',NULL,1,'2026-08-17 13:30:00.000000','2026-08-17 16:30:00.000000','{"inbound_manual_m3": 70.051, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.227871','inbound','В867УХ147','АР306047','8008524218/8008527777',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(529,2,2,'2026-08-17','М612ТН797/ТВ707477',78.613,'manual',NULL,1,'2026-08-17 15:30:00.000000','2026-08-17 17:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 78.613, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.232323','outbound','М612ТН797','ТВ707477','8008521887 8008525793 8008525795',NULL,'8008521887/8008525793/8008525795','30994811',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(530,2,2,'2026-08-18','М952РК161/СА429661',70.89,'mechanized',NULL,1,'2026-08-18 10:00:00.000000','2026-08-18 12:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 70.89, "elco_passports": 1}','2026-09-02 13:45:29.234732','outbound','М952РК161','СА429661','8008529845/8008529847',NULL,NULL,'30994826',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(531,2,2,'2026-08-18','Р552ВО198',4.479,'manual',NULL,1,'2026-08-18 15:00:00.000000','2026-08-18 16:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 4.479, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.236425','outbound','Р552ВО198',NULL,'8008530107/8008530200',NULL,NULL,'30994816',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(532,2,2,'2026-08-19','С156ТМ47',40.742,'manual',NULL,1,'2026-08-19 10:00:00.000000','2026-08-19 13:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 40.742, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.238369','outbound','С156ТМ47',NULL,'8008532548/8008532588/8008533158/8008533349',NULL,NULL,'30994813',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(533,2,2,'2026-08-19','К838КС53/НК135253',92.704,'manual',NULL,1,'2026-08-19 10:40:00.000000','2026-08-19 14:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 92.704, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.240098','outbound','К838КС53','НК135253','8008533375/8008533376',NULL,NULL,'30994817',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(534,2,2,'2026-08-19','С156ТМ47',2.033,'manual',NULL,1,'2026-08-19 14:40:00.000000','2026-08-19 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 2.033, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.241780','outbound','С156ТМ47',NULL,'8008532643/8008532887',NULL,NULL,'30994911',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(535,2,2,'2026-08-19','В867УХ147/АР306047',61.639,'mechanized',NULL,1,'2026-08-19 14:00:00.000000','2026-08-19 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 61.639, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.243574','inbound','В867УХ147','АР306047','8008533211',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(536,2,2,'2026-08-19','К582ВЕ147/ВК298647',45.72,'manual',NULL,1,'2026-08-19 09:00:00.000000','2026-08-19 10:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 45.72, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.245280','outbound','К582ВЕ147','ВК298647','8008533089/8008533160',NULL,NULL,'30994812',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(537,2,2,'2026-08-19','AT34157/A5788E7',69.085,'mechanized',NULL,1,'2026-08-19 10:40:00.000000','2026-08-19 16:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 69.085, "elco_passports": 1}','2026-09-02 13:45:29.249634','outbound','AT34157','A5788E7','8008529862/8008530578',NULL,NULL,'30994920/30994919',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(538,2,2,'2026-08-20','С156ТМ47',14.251,'manual',NULL,1,'2026-08-20 09:20:00.000000','2026-08-20 13:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 14.251, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.251657','outbound','С156ТМ47',NULL,'8008535368/8008535468/8008535487/8008535525/8008535994',NULL,'8008529892/8008533228/8008534371/8008534377','30994806',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(539,2,2,'2026-08-20','О449НТ797/УХ953177',82.013,'manual',NULL,1,'2026-08-20 09:00:00.000000','2026-08-20 13:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 82.013, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.253546','outbound','О449НТ797','УХ953177','8008530185/8008530191/8008533023/8008536066',NULL,NULL,'30994827',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(540,2,2,'2026-08-20','В825УУ47/АТ730447',89.463,'manual',NULL,1,'2026-08-20 09:00:00.000000','2026-08-20 14:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 89.463, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.255079','outbound','В825УУ47','АТ730447','8008529892/8008533228/8008534371/8008534377',NULL,NULL,'30994810/30994809',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(541,2,2,'2026-08-20','О955ХМ161/СВ840261',71.449,'manual',NULL,1,'2026-08-20 12:20:00.000000','2026-08-20 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 71.449, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.256539','outbound','О955ХМ161','СВ840261','8008536113/8008536115/8008536127',NULL,NULL,'30994823',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(542,2,2,'2026-08-20','В306ОВ178/ВВ472447',75.213,'manual',NULL,1,'2026-08-20 10:30:00.000000','2026-08-20 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 75.213, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.258233','outbound','В306ОВ178','ВВ472447','8008531158/8008531210/8008532636/8008533110/8008533910',NULL,NULL,'30994803',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(543,2,2,'2026-08-21','С156ТМ47',4.542,'manual',NULL,1,'2026-08-21 11:30:00.000000','2026-08-21 12:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 4.542, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.259758','outbound','С156ТМ47',NULL,'8008536767/8008537643/8008538175/8008538640',NULL,NULL,'30994808',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(544,2,2,'2026-08-21','К582ВЕ147/ВК298647',55.033,'mechanized',NULL,1,'2026-08-21 11:57:00.000000','2026-08-21 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 55.033, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.261473','inbound','К582ВЕ147','ВК298647','8008538166',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(545,2,2,'2026-08-21','Н202РМ198',10.53,'manual',NULL,1,'2026-08-21 12:50:00.000000','2026-08-21 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 10.53, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 13:45:29.265432','outbound','Н202РМ198',NULL,'8008442881/8008527327',NULL,NULL,'30994801',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(546,2,2,'2026-08-24','Р552ВО198',8.078,'manual',NULL,1,'2026-08-24 09:40:00.000000','2026-08-24 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 8.078, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.267438','outbound','Р552ВО198',NULL,'8008469261',NULL,NULL,'30994805',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(547,2,2,'2026-08-24','Р088ММ40/АМ102540',94.299,'manual',NULL,1,'2026-08-24 12:00:00.000000','2026-08-24 17:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 94.299, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.269389','outbound','Р088ММ40','АМ102540','8008540931/8008540932',NULL,NULL,'30994802',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(548,2,2,'2026-08-25','С156ТМ47',9.397,'manual',NULL,1,'2026-08-25 09:00:00.000000','2026-08-25 10:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 9.397, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.271107','outbound','С156ТМ47',NULL,'8008543131/8008543898/8008543909',NULL,NULL,'30994804',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(549,2,2,'2026-08-25','О216МК198',8.13,'manual',NULL,1,'2026-08-25 09:40:00.000000','2026-08-25 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 8.13, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.272672','outbound','О216МК198',NULL,'8008540875/8008542792/8008543064/8008543258',NULL,NULL,'30994828',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(550,2,2,'2026-08-25','Т207НЕ178',5.486,'manual',NULL,1,'2026-08-25 09:50:00.000000','2026-08-25 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 5.486, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.274484','outbound','Т207НЕ178',NULL,'8008532930/8008532964',NULL,NULL,'30994822',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(551,2,2,'2026-08-25','М616УО196/АУ819966',37.748,'manual',NULL,1,'2026-08-25 09:10:00.000000','2026-08-25 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 37.748, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.275975','outbound','М616УО196','АУ819966','8008543768',NULL,NULL,'30994807',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(552,2,2,'2026-08-25','М338СМ761/СУ153561',33.81,'manual',NULL,1,'2026-08-25 09:50:00.000000','2026-08-25 12:15:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 33.81, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.277675','outbound','М338СМ761','СУ153561','8008543544',NULL,NULL,'30994825',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(553,2,2,'2026-08-25','К582ВЕ147/ВК298647',50.382,'manual',NULL,1,'2026-08-25 12:03:00.000000','2026-08-25 13:30:00.000000','{"inbound_manual_m3": 50.382, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.279541','inbound','К582ВЕ147','ВК298647','8008540882/8008543828','8008531120/8008531149/8008531166',NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(554,2,2,'2026-08-25','Р452ОО62/АМ039662',105.552,'mechanized',NULL,1,'2026-08-25 12:30:00.000000','2026-08-25 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 52.776, "inbound_mech_m3": 0.0, "outbound_mech_m3": 52.776}','2026-09-02 13:45:29.284187','outbound','Р452ОО62','АМ039662','8008531120/8008531149/8008531166','-',NULL,'30994754',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(555,2,2,'2026-08-25','Р028ОН32',7.723,'manual',NULL,1,'2026-08-25 14:50:00.000000','2026-08-25 16:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 7.723, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.288628','outbound','Р028ОН32',NULL,'8008469244',NULL,NULL,'30994757',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(556,2,2,'2026-08-26','К574НЕ147',0.637,'manual',NULL,1,'2026-08-26 09:00:00.000000','2026-08-26 10:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.637, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.290507','outbound','К574НЕ147',NULL,'8008545002/8008546424',NULL,NULL,'30994756',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(557,2,2,'2026-08-26','К582ВЕ147/ВК298647',68.668,'manual',NULL,1,'2026-08-26 09:00:00.000000','2026-08-26 11:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 68.668, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.292037','outbound','К582ВЕ147','ВК298647','8008547242/8008547248',NULL,NULL,'30994780',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(558,2,2,'2026-08-26','О506УУ40/ВН237516',92.683,'manual',NULL,1,'2026-08-26 10:10:00.000000','2026-08-26 14:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 92.683, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.293895','outbound','О506УУ40','ВН237516','8008547163',NULL,NULL,'30994741',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(559,2,2,'2026-08-27','C156ТМ147',4.092,'manual',NULL,1,'2026-08-27 09:00:00.000000','2026-08-27 10:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 4.092, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.295522','outbound','C156ТМ147',NULL,'8008547052/8008547155/8008550526',NULL,NULL,'30994743',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(560,2,2,'2026-08-27','К582ВЕ147/ВК298647',55.614,'manual',NULL,1,'2026-08-27 09:00:00.000000','2026-08-27 10:30:00.000000','{"inbound_manual_m3": 55.614, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.300463','inbound','К582ВЕ147','ВК298647','8008550754/8008550805',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(561,2,2,'2026-08-27','К106УР178',3.979,'manual',NULL,1,'2026-08-27 12:30:00.000000','2026-08-27 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 3.979, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.302581','outbound','К106УР178',NULL,'8008547986/8008548011',NULL,NULL,'30994769',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(562,2,2,'2026-08-28','М256ОК763/ВР823363',21.548,'manual',NULL,1,'2026-08-28 09:00:00.000000','2026-08-28 11:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 21.548, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.304270','outbound','М256ОК763','ВР823363','8008550492',NULL,NULL,'30994770',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(563,2,2,'2026-08-28','В171ВУ178/АН754647',65.559,'manual',NULL,1,'2026-08-28 09:10:00.000000','2026-08-28 12:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 65.559, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.306568','outbound','В171ВУ178','АН754647','8008552215/8008552247/8008553573/8008553576/8008554471',NULL,NULL,'30994744',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(564,2,2,'2026-08-28','Т295АМ39',32.649,'manual',NULL,1,'2026-08-28 14:30:00.000000','2026-08-28 17:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 32.649, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.308259','outbound','Т295АМ39',NULL,'8008540620/8008540659/8008540668/8008552511',NULL,NULL,'30994763',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(565,2,2,'2026-08-31','Р552ВО198',27.377,'manual',NULL,1,'2026-08-31 09:00:00.000000','2026-08-31 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 27.377, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.309757','outbound','Р552ВО198',NULL,'8008550297',NULL,NULL,'30994755',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(566,2,2,'2026-08-31','К941АС53',7.056,'manual',NULL,1,'2026-08-31 09:00:00.000000','2026-08-31 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 7.056, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.311236','outbound','К941АС53',NULL,'8008544629/8008547193/8008547232/8008548428/8008554022/8008557482',NULL,NULL,'30994748',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(567,2,2,'2026-08-31','218CS61/K7161',62.342,'mechanized',NULL,1,'2026-08-31 12:30:00.000000','2026-08-31 16:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 62.342, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.315787','inbound','218CS61','K7161','17061862',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(568,2,2,'2026-08-31','AX30067/A8100E7',57.328,'manual',NULL,1,'2026-08-31 10:00:00.000000','2026-08-31 15:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 57.328, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.318485','outbound','AX30067','A8100E7','8008546706/8008554791/8008555281/8008555779',NULL,NULL,'30994751/30994752',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(569,2,2,'2026-08-31','M853CE26/ЕА510926',69.043,'manual',NULL,1,'2026-08-31 12:20:00.000000','2026-08-31 15:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 69.043, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.320318','outbound','M853CE26','ЕА510926','8008555971/8008555983/8008557797',NULL,NULL,'30994749',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(570,2,2,'2026-08-31','О216МК198',6.48,'manual',NULL,1,'2026-08-31 12:50:00.000000','2026-08-31 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 6.48, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.321993','outbound','О216МК198',NULL,'8008554736',NULL,NULL,'30994774',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(571,2,2,'2026-08-31','Х676ЕХ797/УХ117377',54.5,'manual',NULL,1,'2026-08-31 12:30:00.000000','2026-08-31 16:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 54.5, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.323809','outbound','Х676ЕХ797','УХ117377','8008552221/8008554476/8008554481/8008554488/8008554492/8008555469/8008555972',NULL,NULL,'30994766',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(572,2,2,'2026-08-31','С480НС67/74AEG10',66.374,'manual',NULL,1,'2026-08-31 13:10:00.000000','2026-08-31 17:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 66.374, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 13:45:29.325613','outbound','С480НС67','74AEG10','8008543546',NULL,NULL,'30994768',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(573,2,2,'2026-08-03','А613СС198',9.852,'manual',NULL,2,'2026-08-03 12:30:00.000000','2026-08-03 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 9.852, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:50.959103','outbound','А613СС198',NULL,'8008501729/8008502144',NULL,NULL,'30994868',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(574,2,2,'2026-08-03','218CS61/M7161',90.96,'mechanized',NULL,2,'2026-08-03 09:30:00.000000','2026-08-03 15:10:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 90.96, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:50.965216','inbound','218CS61','M7161','17056644',NULL,NULL,'0','56644',NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(575,2,2,'2026-08-03','В867УХ147/АР306047',69.344,'mechanized',NULL,2,'2026-08-03 14:00:00.000000','2026-08-03 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 69.344, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:50.967790','inbound','В867УХ147','АР306047','8008488528',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(576,2,2,'2026-08-03','Т375РР198/ЕА939978',67.33,'mechanized',NULL,2,'2026-08-03 13:00:00.000000','2026-08-03 15:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 67.33, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:50.970208','inbound','Т375РР198','ЕА939978','8008498730/8008502166/8008504757',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(577,2,2,'2026-08-03','219CS61/Z6481',71.953,'mechanized',NULL,2,'2026-08-03 12:30:00.000000','2026-08-03 16:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 71.953, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:50.972777','inbound','219CS61','Z6481','17056777',NULL,NULL,'0','56777',NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(578,2,2,'2026-08-04','К582ВЕ147/ВК298647',55.014,'mechanized',NULL,2,'2026-08-04 11:30:00.000000','2026-08-04 12:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 55.014, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:50.978010','inbound','К582ВЕ147','ВК298647','8008488531',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(579,2,2,'2026-08-04','В867УХ147/АР306047',69.284,'mechanized',NULL,2,'2026-08-04 12:30:00.000000','2026-08-04 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 69.284, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:50.981145','inbound','В867УХ147','АР306047','8008488530',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(580,2,2,'2026-08-04','К725ТХ126/СВ472726',26.237,'manual',NULL,2,'2026-08-04 13:30:00.000000','2026-08-04 15:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 26.237, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:50.983806','outbound','К725ТХ126','СВ472726','8008505170',NULL,NULL,'30994869',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(581,2,2,'2026-08-04','К526ЕК53/НК805453',68.625,'manual',NULL,2,'2026-08-04 13:00:00.000000','2026-08-04 16:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 68.625, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:50.986240','outbound','К526ЕК53','НК805453','8008505960',NULL,NULL,'30994863',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(582,2,2,'2026-08-05','О216МК198',11.783,'manual',NULL,2,'2026-08-05 09:30:00.000000','2026-08-05 10:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 11.783, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:50.988657','outbound','О216МК198',NULL,'8008505270/8008508258',NULL,NULL,'30994858',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(583,2,2,'2026-08-05','С156ТМ47',8.561,'manual',NULL,2,'2026-08-05 09:00:00.000000','2026-08-05 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 8.561, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:50.993359','outbound','С156ТМ47',NULL,'8008496265/8008501544/8008501548/8008502023/8008504415/8008508297',NULL,NULL,'30994855',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(584,2,2,'2026-08-05','О462ХР196/ВА173059',88.113,'manual',NULL,2,'2026-08-05 09:00:00.000000','2026-08-05 13:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 88.113, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:50.998276','outbound','О462ХР196','ВА173059','8008508594/8008508625/8008508626',NULL,NULL,'30994854',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(585,2,2,'2026-08-05','К810НО53/НМ010853',93.241,'manual',NULL,2,'2026-08-05 09:00:00.000000','2026-08-05 13:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 93.241, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.001301','outbound','К810НО53','НМ010853','8008506031/8008506032/8008506375',NULL,NULL,'30994859',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(586,2,2,'2026-08-05','М900РС163/АУ601163',18.76,'manual',NULL,2,'2026-08-05 13:00:00.000000','2026-08-05 15:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 18.76, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.004217','outbound','М900РС163','АУ601163','8008505351',NULL,NULL,'30994852',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(587,2,2,'2026-08-05','А954ОА134/ВТ603634',62.913,'manual',NULL,2,'2026-08-05 12:00:00.000000','2026-08-05 15:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 62.913, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.008455','outbound','А954ОА134','ВТ603634','8008494308/8008502285/8008505956',NULL,NULL,'30994857',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(588,2,2,'2026-08-06','С156ТМ47',0.579,'manual',NULL,2,'2026-08-06 09:00:00.000000','2026-08-06 10:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.579, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.012464','outbound','С156ТМ47',NULL,'8008508905',NULL,NULL,'30994888',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(589,2,2,'2026-08-06','О216МК198',8.246,'manual',NULL,2,'2026-08-06 09:00:00.000000','2026-08-06 10:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 8.246, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.015481','outbound','О216МК198',NULL,'8008509621/8008510944',NULL,NULL,'30994872',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(590,2,2,'2026-08-06','В867УХ147/АР306047',61.459,'mechanized',NULL,2,'2026-08-06 12:40:00.000000','2026-08-06 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 61.459, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.018117','inbound','В867УХ147','АР306047','8008488546',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(591,2,2,'2026-08-06','К106УР178',0.81,'mechanized',NULL,2,'2026-08-06 15:00:00.000000','2026-08-06 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.81, "elco_passports": 1}','2026-09-02 14:40:51.020759','outbound','К106УР178',NULL,'8008509141',NULL,NULL,'30994851',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(592,2,2,'2026-08-06','К582ВЕ147/ВК298647',62.429,'mechanized',NULL,2,'2026-08-06 14:30:00.000000','2026-08-06 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 62.429, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.026328','inbound','К582ВЕ147','ВК298647','8008488545',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(593,2,2,'2026-08-07','В867УХ147/АР306047',56.983,'mechanized',NULL,2,'2026-08-07 09:00:00.000000','2026-08-07 10:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 56.983, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.029481','inbound','В867УХ147','АР306047','8008488535/8008513662',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(594,2,2,'2026-08-07','У848МО761/СН339161',31.717,'manual',NULL,2,'2026-08-07 09:00:00.000000','2026-08-07 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 31.717, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.032044','outbound','У848МО761','СН339161','8008511318',NULL,NULL,'30994844',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(595,2,2,'2026-08-07','Т375РР198/ЕА939978',65.173,'mechanized',NULL,1,'2026-08-07 13:00:00.000000','2026-08-07 14:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 65.173, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.034512','inbound','Т375РР198','ЕА939978','8008488542',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(596,2,2,'2026-08-07','О216МК198',0.633,'manual',NULL,1,'2026-08-07 14:00:00.000000','2026-08-07 15:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.633, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.036833','outbound','О216МК198',NULL,'8008510761/8008513470',NULL,NULL,'30994849',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(597,2,2,'2026-08-07','BB17427/A5315I7',51.5,'manual',NULL,1,'2026-08-07 11:30:00.000000','2026-08-07 16:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 51.5, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.039666','outbound','BB17427','A5315I7','8008510641/8008510647/8008510653/8008513120/8008513131/8008513466',NULL,NULL,'30994845',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(598,2,2,'2026-08-10','Р552ВО198',39.384,'manual',NULL,1,'2026-08-10 09:40:00.000000','2026-08-10 11:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 39.384, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.045511','outbound','Р552ВО198',NULL,'8008514702/8008515608',NULL,NULL,'30994846',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(599,2,2,'2026-08-10','В867УХ147/АР306047',46.072,'mechanized',NULL,1,'2026-08-10 12:00:00.000000','2026-08-10 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 46.072, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.048267','inbound','В867УХ147','АР306047','8008480507/8008516142',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(600,2,2,'2026-08-10','А444СН36/ВЕ038936',58.283,'manual',NULL,1,'2026-08-10 11:30:00.000000','2026-08-10 14:30:00.000000','{"inbound_manual_m3": 58.283, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.050630','outbound','А444СН36','ВЕ038936','8008515545/8008515929',NULL,NULL,'30994842',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(601,2,2,'2026-08-10','B713CT134/ЕА230834',56.205,'manual',NULL,1,'2026-08-10 12:00:00.000000','2026-08-10 15:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 56.205, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.053029','outbound','B713CT134','ЕА230834','8008501500/8008509617/8008514288/8008514392/8008514680',NULL,NULL,'30994833',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(602,2,2,'2026-08-10','К106УР178',0.81,'mechanized',NULL,1,'2026-08-10 13:30:00.000000','2026-08-10 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.81, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.055418','inbound','К106УР178',NULL,'84938085',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(603,2,2,'2026-08-11','C010OK198/ЕЕ043778',70.226,'manual',NULL,1,'2026-08-11 09:30:00.000000','2026-08-11 13:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 70.226, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.059273','outbound','C010OK198','ЕЕ043778','8008516713/8008518354',NULL,NULL,'30994834',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(604,2,2,'2026-08-11','В867УХ147/АР306047',66.355,'manual',NULL,1,'2026-08-11 12:00:00.000000','2026-08-11 14:30:00.000000','{"inbound_manual_m3": 66.355, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.062359','inbound','В867УХ147','АР306047','8008517796',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(605,2,2,'2026-08-11','АС6427-1  MI590YI',88.56,'manual',NULL,1,'2026-08-11 09:00:00.000000','2026-08-11 15:00:00.000000','{"inbound_manual_m3": 88.56, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.064830','inbound','АС6427-1  MI590YI',NULL,'17058956',NULL,NULL,'0','58956',NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(606,2,2,'2026-08-12','Т375РР198/ЕА939978',66.912,'manual',NULL,1,'2026-08-12 09:00:00.000000','2026-08-12 11:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 66.912, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.067043','outbound','Т375РР198','ЕА939978','8008520547/8008520551/8008520554/8008520788/8008520874',NULL,NULL,'30994836',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(607,2,2,'2026-08-12','219CS61/T7116',91.91,'mechanized',NULL,1,'2026-08-12 09:00:00.000000','2026-08-12 13:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 91.91, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.069293','inbound','219CS61','T7116','17059305',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(608,2,2,'2026-08-12','М738ТА716/ВС041016',94.151,'mechanized',NULL,1,'2026-08-12 09:00:00.000000','2026-08-12 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 94.151, "elco_passports": 1}','2026-09-02 14:40:51.071906','outbound','М738ТА716','ВС041016','8008520789/8008520790/8008520932',NULL,NULL,'30994835',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(609,2,2,'2026-08-12','В867УХ147/АР306047',60.515,'mechanized',NULL,1,'2026-08-12 12:30:00.000000','2026-08-12 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 60.515, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.075611','inbound','В867УХ147','АР306047','8008519004',NULL,NULL,'0','519004',NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(610,2,2,'2026-08-12','Р548УХ198/ВТ413078',69.57,'mechanized',NULL,1,'2026-08-12 12:30:00.000000','2026-08-12 14:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 69.57, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.078789','inbound','Р548УХ198','ВТ413078','8008421443',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(611,2,2,'2026-08-13','Н202РМ198',4.901,'manual',NULL,1,'2026-08-13 09:00:00.000000','2026-08-13 10:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 4.901, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.081267','outbound','Н202РМ198',NULL,'8008521320',NULL,NULL,'30994831',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(612,2,2,'2026-08-13','Т375РР198/ЕА939978',60.399,'manual',NULL,1,'2026-08-13 12:30:00.000000','2026-08-13 14:30:00.000000','{"inbound_manual_m3": 60.399, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.083785','inbound','Т375РР198','ЕА939978','8008519006',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(613,2,2,'2026-08-13','В867УХ147/АР306047',61.494,'mechanized',NULL,1,'2026-08-13 12:30:00.000000','2026-08-13 14:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 61.494, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.086248','inbound','В867УХ147','АР306047','8008519007/8008523521',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(614,2,2,'2026-08-13','АВ90091/1TL5671',87,'mechanized',NULL,1,'2026-08-13 09:00:00.000000','2026-08-13 14:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 87.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.088719','inbound','АВ90091','1TL5671','17057008',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(615,2,2,'2026-08-13','Т131СЕ178',14.478,'manual',NULL,1,'2026-08-13 15:00:00.000000','2026-08-13 16:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 14.478, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.092639','outbound','Т131СЕ178',NULL,'8008518227/8008519145/8008520302/8008521255/8008521261/8008521269/8008523526',NULL,NULL,'30994861',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(616,2,2,'2026-08-14','В171ВУ178/АН754647',60.36,'manual',NULL,1,'2026-08-14 09:30:00.000000','2026-08-14 11:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 60.36, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.095757','outbound','В171ВУ178','АН754647','8008524305/8008524310/8008524383/8008525699/8008526341/8008526595',NULL,NULL,'30994814',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(617,2,2,'2026-08-14','В867УХ147/АР306047',51.976,'manual',NULL,1,'2026-08-14 13:10:00.000000','2026-08-14 14:20:00.000000','{"inbound_manual_m3": 51.976, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.098217','inbound','В867УХ147','АР306047','8008524127',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(618,2,2,'2026-08-14','К582ВЕ147/ВК298647',50.309,'manual',NULL,1,'2026-08-14 12:00:00.000000','2026-08-14 14:30:00.000000','{"inbound_manual_m3": 50.309, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.100620','inbound','К582ВЕ147','ВК298647','8008519012/8008525798',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(619,2,2,'2026-08-17','Н202РМ198',10.546,'mechanized',NULL,1,'2026-08-17 09:30:00.000000','2026-08-17 10:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 10.546, "elco_passports": 1}','2026-09-02 14:40:51.103438','outbound','Н202РМ198',NULL,'8008520542/8008521306',NULL,NULL,'30994829',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(620,2,2,'2026-08-17','С156ТМ47',3.437,'manual',NULL,1,'2026-08-17 10:00:00.000000','2026-08-17 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 3.437, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.105863','outbound','С156ТМ47',NULL,'8008526383/8008526388/8008527817',NULL,NULL,'30994818',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(621,2,2,'2026-08-17','Н349НК26/СВ517126',71.25,'manual',NULL,1,'2026-08-17 13:30:00.000000','2026-08-17 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 71.25, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.110705','outbound','Н349НК26','СВ517126','8008527673/8008527698',NULL,NULL,'30994830',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(622,2,2,'2026-08-17','В867УХ147/АР306047',70.051,'manual',NULL,1,'2026-08-17 13:30:00.000000','2026-08-17 16:30:00.000000','{"inbound_manual_m3": 70.051, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.113700','inbound','В867УХ147','АР306047','8008524218/8008527777',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(623,2,2,'2026-08-17','М612ТН797/ТВ707477',78.613,'manual',NULL,1,'2026-08-17 15:30:00.000000','2026-08-17 17:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 78.613, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.116371','outbound','М612ТН797','ТВ707477','8008521887 8008525793 8008525795',NULL,'8008521887/8008525793/8008525795','30994811',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(624,2,2,'2026-08-18','М952РК161/СА429661',70.89,'mechanized',NULL,1,'2026-08-18 10:00:00.000000','2026-08-18 12:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 70.89, "elco_passports": 1}','2026-09-02 14:40:51.119653','outbound','М952РК161','СА429661','8008529845/8008529847',NULL,NULL,'30994826',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(625,2,2,'2026-08-18','Р552ВО198',4.479,'manual',NULL,1,'2026-08-18 15:00:00.000000','2026-08-18 16:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 4.479, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.122521','outbound','Р552ВО198',NULL,'8008530107/8008530200',NULL,NULL,'30994816',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(626,2,2,'2026-08-19','С156ТМ47',40.742,'manual',NULL,1,'2026-08-19 10:00:00.000000','2026-08-19 13:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 40.742, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.128634','outbound','С156ТМ47',NULL,'8008532548/8008532588/8008533158/8008533349',NULL,NULL,'30994813',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(627,2,2,'2026-08-19','К838КС53/НК135253',92.704,'manual',NULL,1,'2026-08-19 10:40:00.000000','2026-08-19 14:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 92.704, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.131382','outbound','К838КС53','НК135253','8008533375/8008533376',NULL,NULL,'30994817',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(628,2,2,'2026-08-19','С156ТМ47',2.033,'manual',NULL,1,'2026-08-19 14:40:00.000000','2026-08-19 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 2.033, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.134734','outbound','С156ТМ47',NULL,'8008532643/8008532887',NULL,NULL,'30994911',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(629,2,2,'2026-08-19','В867УХ147/АР306047',61.639,'mechanized',NULL,1,'2026-08-19 14:00:00.000000','2026-08-19 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 61.639, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.137476','inbound','В867УХ147','АР306047','8008533211',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(630,2,2,'2026-08-19','К582ВЕ147/ВК298647',45.72,'manual',NULL,1,'2026-08-19 09:00:00.000000','2026-08-19 10:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 45.72, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.143909','outbound','К582ВЕ147','ВК298647','8008533089/8008533160',NULL,NULL,'30994812',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(631,2,2,'2026-08-19','AT34157/A5788E7',69.085,'mechanized',NULL,1,'2026-08-19 10:40:00.000000','2026-08-19 16:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 69.085, "elco_passports": 1}','2026-09-02 14:40:51.148738','outbound','AT34157','A5788E7','8008529862/8008530578',NULL,NULL,'30994920/30994919',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(632,2,2,'2026-08-20','С156ТМ47',14.251,'manual',NULL,1,'2026-08-20 09:20:00.000000','2026-08-20 13:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 14.251, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.151875','outbound','С156ТМ47',NULL,'8008535368/8008535468/8008535487/8008535525/8008535994',NULL,'8008529892/8008533228/8008534371/8008534377','30994806',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(633,2,2,'2026-08-20','О449НТ797/УХ953177',82.013,'manual',NULL,1,'2026-08-20 09:00:00.000000','2026-08-20 13:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 82.013, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.155231','outbound','О449НТ797','УХ953177','8008530185/8008530191/8008533023/8008536066',NULL,NULL,'30994827',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(634,2,2,'2026-08-20','В825УУ47/АТ730447',89.463,'manual',NULL,1,'2026-08-20 09:00:00.000000','2026-08-20 14:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 89.463, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.164672','outbound','В825УУ47','АТ730447','8008529892/8008533228/8008534371/8008534377',NULL,NULL,'30994810/30994809',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(635,2,2,'2026-08-20','О955ХМ161/СВ840261',71.449,'manual',NULL,1,'2026-08-20 12:20:00.000000','2026-08-20 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 71.449, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.167623','outbound','О955ХМ161','СВ840261','8008536113/8008536115/8008536127',NULL,NULL,'30994823',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(636,2,2,'2026-08-20','В306ОВ178/ВВ472447',75.213,'manual',NULL,1,'2026-08-20 10:30:00.000000','2026-08-20 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 75.213, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.170373','outbound','В306ОВ178','ВВ472447','8008531158/8008531210/8008532636/8008533110/8008533910',NULL,NULL,'30994803',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(637,2,2,'2026-08-21','С156ТМ47',4.542,'manual',NULL,1,'2026-08-21 11:30:00.000000','2026-08-21 12:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 4.542, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.178327','outbound','С156ТМ47',NULL,'8008536767/8008537643/8008538175/8008538640',NULL,NULL,'30994808',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(638,2,2,'2026-08-21','К582ВЕ147/ВК298647',55.033,'mechanized',NULL,1,'2026-08-21 11:57:00.000000','2026-08-21 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 55.033, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.182155','inbound','К582ВЕ147','ВК298647','8008538166',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(639,2,2,'2026-08-21','Н202РМ198',10.53,'manual',NULL,1,'2026-08-21 12:50:00.000000','2026-08-21 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 10.53, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0, "elco_passports": 1}','2026-09-02 14:40:51.185495','outbound','Н202РМ198',NULL,'8008442881/8008527327',NULL,NULL,'30994801',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(640,2,2,'2026-08-24','Р552ВО198',8.078,'manual',NULL,1,'2026-08-24 09:40:00.000000','2026-08-24 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 8.078, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.189269','outbound','Р552ВО198',NULL,'8008469261',NULL,NULL,'30994805',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(641,2,2,'2026-08-24','Р088ММ40/АМ102540',94.299,'manual',NULL,1,'2026-08-24 12:00:00.000000','2026-08-24 17:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 94.299, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.197587','outbound','Р088ММ40','АМ102540','8008540931/8008540932',NULL,NULL,'30994802',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(642,2,2,'2026-08-25','С156ТМ47',9.397,'manual',NULL,1,'2026-08-25 09:00:00.000000','2026-08-25 10:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 9.397, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.200276','outbound','С156ТМ47',NULL,'8008543131/8008543898/8008543909',NULL,NULL,'30994804',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(643,2,2,'2026-08-25','О216МК198',8.13,'manual',NULL,1,'2026-08-25 09:40:00.000000','2026-08-25 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 8.13, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.203150','outbound','О216МК198',NULL,'8008540875/8008542792/8008543064/8008543258',NULL,NULL,'30994828',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(644,2,2,'2026-08-25','Т207НЕ178',5.486,'manual',NULL,1,'2026-08-25 09:50:00.000000','2026-08-25 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 5.486, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.206072','outbound','Т207НЕ178',NULL,'8008532930/8008532964',NULL,NULL,'30994822',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(645,2,2,'2026-08-25','М616УО196/АУ819966',37.748,'manual',NULL,1,'2026-08-25 09:10:00.000000','2026-08-25 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 37.748, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.212593','outbound','М616УО196','АУ819966','8008543768',NULL,NULL,'30994807',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(646,2,2,'2026-08-25','М338СМ761/СУ153561',33.81,'manual',NULL,1,'2026-08-25 09:50:00.000000','2026-08-25 12:15:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 33.81, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.215410','outbound','М338СМ761','СУ153561','8008543544',NULL,NULL,'30994825',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(647,2,2,'2026-08-25','К582ВЕ147/ВК298647',50.382,'manual',NULL,1,'2026-08-25 12:03:00.000000','2026-08-25 13:30:00.000000','{"inbound_manual_m3": 50.382, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.217837','inbound','К582ВЕ147','ВК298647','8008540882/8008543828','8008531120/8008531149/8008531166',NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(648,2,2,'2026-08-25','Р452ОО62/АМ039662',105.552,'mechanized',NULL,1,'2026-08-25 12:30:00.000000','2026-08-25 15:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 52.776, "inbound_mech_m3": 0.0, "outbound_mech_m3": 52.776}','2026-09-02 14:40:51.220505','outbound','Р452ОО62','АМ039662','8008531120/8008531149/8008531166','-',NULL,'30994754',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(649,2,2,'2026-08-25','Р028ОН32',7.723,'manual',NULL,1,'2026-08-25 14:50:00.000000','2026-08-25 16:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 7.723, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.229482','outbound','Р028ОН32',NULL,'8008469244',NULL,NULL,'30994757',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(650,2,2,'2026-08-26','К574НЕ147',0.637,'manual',NULL,1,'2026-08-26 09:00:00.000000','2026-08-26 10:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.637, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.232084','outbound','К574НЕ147',NULL,'8008545002/8008546424',NULL,NULL,'30994756',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(651,2,2,'2026-08-26','К582ВЕ147/ВК298647',68.668,'manual',NULL,1,'2026-08-26 09:00:00.000000','2026-08-26 11:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 68.668, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.234587','outbound','К582ВЕ147','ВК298647','8008547242/8008547248',NULL,NULL,'30994780',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(652,2,2,'2026-08-26','О506УУ40/ВН237516',92.683,'manual',NULL,1,'2026-08-26 10:10:00.000000','2026-08-26 14:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 92.683, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.237325','outbound','О506УУ40','ВН237516','8008547163',NULL,NULL,'30994741',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(653,2,2,'2026-08-27','C156ТМ147',4.092,'manual',NULL,1,'2026-08-27 09:00:00.000000','2026-08-27 10:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 4.092, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.243755','outbound','C156ТМ147',NULL,'8008547052/8008547155/8008550526',NULL,NULL,'30994743',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(654,2,2,'2026-08-27','К582ВЕ147/ВК298647',55.614,'manual',NULL,1,'2026-08-27 09:00:00.000000','2026-08-27 10:30:00.000000','{"inbound_manual_m3": 55.614, "outbound_manual_m3": 0.0, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.246741','inbound','К582ВЕ147','ВК298647','8008550754/8008550805',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(655,2,2,'2026-08-27','К106УР178',3.979,'manual',NULL,1,'2026-08-27 12:30:00.000000','2026-08-27 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 3.979, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.249417','outbound','К106УР178',NULL,'8008547986/8008548011',NULL,NULL,'30994769',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(656,2,2,'2026-08-28','М256ОК763/ВР823363',21.548,'manual',NULL,1,'2026-08-28 09:00:00.000000','2026-08-28 11:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 21.548, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.252030','outbound','М256ОК763','ВР823363','8008550492',NULL,NULL,'30994770',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(657,2,2,'2026-08-28','В171ВУ178/АН754647',65.559,'manual',NULL,1,'2026-08-28 09:10:00.000000','2026-08-28 12:30:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 65.559, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.254544','outbound','В171ВУ178','АН754647','8008552215/8008552247/8008553573/8008553576/8008554471',NULL,NULL,'30994744',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(658,2,2,'2026-08-28','Т295АМ39',32.649,'manual',NULL,1,'2026-08-28 14:30:00.000000','2026-08-28 17:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 32.649, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.259102','outbound','Т295АМ39',NULL,'8008540620/8008540659/8008540668/8008552511',NULL,NULL,'30994763',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(659,2,2,'2026-08-31','Р552ВО198',27.377,'manual',NULL,1,'2026-08-31 09:00:00.000000','2026-08-31 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 27.377, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.262729','outbound','Р552ВО198',NULL,'8008550297',NULL,NULL,'30994755',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(660,2,2,'2026-08-31','К941АС53',7.056,'manual',NULL,1,'2026-08-31 09:00:00.000000','2026-08-31 11:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 7.056, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.265844','outbound','К941АС53',NULL,'8008544629/8008547193/8008547232/8008548428/8008554022/8008557482',NULL,NULL,'30994748',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(661,2,2,'2026-08-31','218CS61/K7161',62.342,'mechanized',NULL,1,'2026-08-31 12:30:00.000000','2026-08-31 16:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 0.0, "inbound_mech_m3": 62.342, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.284629','inbound','218CS61','K7161','17061862',NULL,NULL,'0',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(662,2,2,'2026-08-31','AX30067/A8100E7',57.328,'manual',NULL,1,'2026-08-31 10:00:00.000000','2026-08-31 15:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 57.328, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.287571','outbound','AX30067','A8100E7','8008546706/8008554791/8008555281/8008555779',NULL,NULL,'30994751/30994752',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(663,2,2,'2026-08-31','M853CE26/ЕА510926',69.043,'manual',NULL,1,'2026-08-31 12:20:00.000000','2026-08-31 15:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 69.043, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.291619','outbound','M853CE26','ЕА510926','8008555971/8008555983/8008557797',NULL,NULL,'30994749',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(664,2,2,'2026-08-31','О216МК198',6.48,'manual',NULL,1,'2026-08-31 12:50:00.000000','2026-08-31 14:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 6.48, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.295427','outbound','О216МК198',NULL,'8008554736',NULL,NULL,'30994774',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(665,2,2,'2026-08-31','Х676ЕХ797/УХ117377',54.5,'manual',NULL,1,'2026-08-31 12:30:00.000000','2026-08-31 16:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 54.5, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.298727','outbound','Х676ЕХ797','УХ117377','8008552221/8008554476/8008554481/8008554488/8008554492/8008555469/8008555972',NULL,NULL,'30994766',NULL,NULL,'manual',NULL);
INSERT INTO "vehicle_operations" VALUES(666,2,2,'2026-08-31','С480НС67/74AEG10',66.374,'manual',NULL,1,'2026-08-31 13:10:00.000000','2026-08-31 17:00:00.000000','{"inbound_manual_m3": 0.0, "outbound_manual_m3": 66.374, "inbound_mech_m3": 0.0, "outbound_mech_m3": 0.0}','2026-09-02 14:40:51.301222','outbound','С480НС67','74AEG10','8008543546',NULL,NULL,'30994768',NULL,NULL,'manual',NULL);
CREATE TABLE vehicle_plates (
	id INTEGER NOT NULL, 
	plate_number VARCHAR(32) NOT NULL, 
	vehicle_type VARCHAR(64), 
	is_active BOOLEAN DEFAULT 1, 
	PRIMARY KEY (id), 
	UNIQUE (plate_number)
);
CREATE TABLE vehicle_types (
	id INTEGER NOT NULL, 
	code VARCHAR(64) NOT NULL, 
	name VARCHAR(256) NOT NULL, 
	sort_order INTEGER DEFAULT '0' NOT NULL, dimensions_label VARCHAR(128), 
	PRIMARY KEY (id), 
	UNIQUE (code)
);
INSERT INTO "vehicle_types" VALUES(1,'truck','Авто 82м³',10,'13,6×2,45×2,70');
INSERT INTO "vehicle_types" VALUES(2,'gazelle','Газель',30,'6,0×2,1×2,2');
INSERT INTO "vehicle_types" VALUES(3,'van','Фургон',40,'4,2×2,0×2,2');
INSERT INTO "vehicle_types" VALUES(4,'container','НС 45′',20,'13,6×2,45×2,70');
INSERT INTO "vehicle_types" VALUES(5,'tent','Тент',50,'13,6×2,45×2,70');
INSERT INTO "vehicle_types" VALUES(6,'refrigerator','Рефрижератор',60,'13,6×2,45×2,70');
INSERT INTO "vehicle_types" VALUES(7,'other','Прочее',99,NULL);
CREATE TABLE vehicle_waybills (
	id INTEGER NOT NULL, 
	vehicle_operation_id INTEGER NOT NULL, 
	waybill_number VARCHAR(256), 
	mx_number VARCHAR(256), 
	sort_order INTEGER DEFAULT '0' NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(vehicle_operation_id) REFERENCES vehicle_operations (id) ON DELETE CASCADE
);
INSERT INTO "vehicle_waybills" VALUES(381,2,'8008501729/8008502144',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(382,3,'17056644',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(383,4,'8008488528',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(384,5,'8008498730/8008502166/8008504757',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(385,6,'17056777',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(386,7,'8008488531',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(387,8,'8008488530',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(388,9,'8008505170',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(389,10,'8008505960',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(390,11,'8008505270/8008508258',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(391,12,'8008496265/8008501544/8008501548/8008502023/8008504415/8008508297',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(392,13,'8008508594/8008508625/8008508626',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(393,14,'8008506031/8008506032/8008506375',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(394,15,'8008505351',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(395,16,'8008494308/8008502285/8008505956',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(396,17,'8008508905',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(397,18,'8008509621/8008510944',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(398,19,'8008488546',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(399,20,'8008509141',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(400,21,'8008488545',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(401,22,'8008488535/8008513662',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(402,23,'8008511318',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(403,24,'8008488542',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(404,25,'8008510761/8008513470',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(405,26,'8008510641/8008510647/8008510653/8008513120/8008513131/8008513466',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(406,27,'8008514702/8008515608',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(407,28,'8008480507/8008516142',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(408,29,'8008515545/8008515929',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(409,30,'8008501500/8008509617/8008514288/8008514392/8008514680',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(410,31,'84938085',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(411,32,'8008516713/8008518354',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(412,33,'8008517796',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(413,34,'17058956',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(414,35,'8008520547/8008520551/8008520554/8008520788/8008520874',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(415,36,'17059305',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(416,37,'8008520789/8008520790/8008520932',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(417,38,'8008519004',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(418,39,'8008421443',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(419,40,'8008521320',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(420,41,'8008519006',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(421,42,'8008519007/8008523521',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(422,43,'17057008',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(423,44,'8008518227/8008519145/8008520302/8008521255/8008521261/8008521269/8008523526',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(424,45,'8008524305/8008524310/8008524383/8008525699/8008526341/8008526595',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(425,46,'8008524127',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(426,47,'8008519012/8008525798',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(427,48,'8008520542/8008521306',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(428,49,'8008526383/8008526388/8008527817',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(429,50,'8008527673/8008527698',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(430,51,'8008524218/8008527777',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(431,52,'8008521887 8008525793 8008525795','8008521887/8008525793/8008525795',0);
INSERT INTO "vehicle_waybills" VALUES(432,53,'8008529845/8008529847',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(433,54,'8008530107/8008530200',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(434,55,'8008532548/8008532588/8008533158/8008533349',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(435,56,'8008533375/8008533376',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(436,57,'8008532643/8008532887',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(437,58,'8008533211',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(438,59,'8008533089/8008533160',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(439,60,'8008529862/8008530578',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(440,61,'8008535368/8008535468/8008535487/8008535525/8008535994','8008529892/8008533228/8008534371/8008534377',0);
INSERT INTO "vehicle_waybills" VALUES(441,62,'8008530185/8008530191/8008533023/8008536066',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(442,63,'8008529892/8008533228/8008534371/8008534377',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(443,64,'8008536113/8008536115/8008536127',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(444,65,'8008531158/8008531210/8008532636/8008533110/8008533910',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(445,66,'8008536767/8008537643/8008538175/8008538640',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(446,67,'8008538166',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(447,68,'8008442881/8008527327',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(448,69,'8008469261',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(449,70,'8008540931/8008540932',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(450,71,'8008543131/8008543898/8008543909',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(451,72,'8008540875/8008542792/8008543064/8008543258',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(452,73,'8008532930/8008532964',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(453,74,'8008543768',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(454,75,'8008543544',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(455,76,'8008540882/8008543828','8008531120/8008531149/8008531166',0);
INSERT INTO "vehicle_waybills" VALUES(456,77,'8008531120/8008531149/8008531166',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(457,78,'8008531120/8008531149/8008531166','-',0);
INSERT INTO "vehicle_waybills" VALUES(458,79,'8008469244',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(459,80,'8008545002/8008546424',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(460,81,'8008547242/8008547248',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(461,82,'8008547163',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(462,83,'8008547052/8008547155/8008550526',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(463,84,'8008550754/8008550805',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(464,85,'8008547986/8008548011',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(465,86,'8008550492',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(466,87,'8008552215/8008552247/8008553573/8008553576/8008554471',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(467,88,'8008540620/8008540659/8008540668/8008552511',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(468,89,'8008550297',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(469,90,'8008544629/8008547193/8008547232/8008548428/8008554022/8008557482',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(470,91,'17061862',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(471,92,'8008546706/8008554791/8008555281/8008555779',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(472,93,'8008555971/8008555983/8008557797',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(473,94,'8008554736',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(474,95,'8008552221/8008554476/8008554481/8008554488/8008554492/8008555469/8008555972',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(475,96,'8008543546',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1520,192,'8008543546',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1803,98,'8008501729/8008502144',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1804,99,'17056644',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1805,100,'8008488528',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1806,101,'8008498730/8008502166/8008504757',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1807,102,'17056777',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1808,103,'8008488531',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1809,104,'8008488530',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1810,105,'8008505170',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1811,106,'8008505960',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1812,107,'8008505270/8008508258',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1813,108,'8008496265/8008501544/8008501548/8008502023/8008504415/8008508297',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1814,109,'8008508594/8008508625/8008508626',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1815,110,'8008506031/8008506032/8008506375',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1816,111,'8008505351',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1817,112,'8008494308/8008502285/8008505956',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1818,113,'8008508905',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1819,114,'8008509621/8008510944',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1820,115,'8008488546',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1821,116,'8008509141',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1822,117,'8008488545',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1823,118,'8008488535/8008513662',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1824,119,'8008511318',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1825,120,'8008488542',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1826,121,'8008510761/8008513470',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1827,122,'8008510641/8008510647/8008510653/8008513120/8008513131/8008513466',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1828,123,'8008514702/8008515608',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1829,124,'8008480507/8008516142',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1830,125,'8008515545/8008515929',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1831,126,'8008501500/8008509617/8008514288/8008514392/8008514680',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1832,127,'84938085',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1833,128,'8008516713/8008518354',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1834,129,'8008517796',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1835,130,'17058956',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1836,131,'8008520547/8008520551/8008520554/8008520788/8008520874',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1837,132,'17059305',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1838,133,'8008520789/8008520790/8008520932',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1839,134,'8008519004',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1840,135,'8008421443',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1841,136,'8008521320',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1842,137,'8008519006',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1843,138,'8008519007/8008523521',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1844,139,'17057008',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1845,140,'8008518227/8008519145/8008520302/8008521255/8008521261/8008521269/8008523526',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1846,141,'8008524305/8008524310/8008524383/8008525699/8008526341/8008526595',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1847,142,'8008524127',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1848,143,'8008519012/8008525798',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1849,144,'8008520542/8008521306',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1850,145,'8008526383/8008526388/8008527817',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1851,146,'8008527673/8008527698',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1852,147,'8008524218/8008527777',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1853,148,'8008521887 8008525793 8008525795','8008521887/8008525793/8008525795',0);
INSERT INTO "vehicle_waybills" VALUES(1854,149,'8008529845/8008529847',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1855,150,'8008530107/8008530200',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1856,151,'8008532548/8008532588/8008533158/8008533349',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1857,152,'8008533375/8008533376',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1858,153,'8008532643/8008532887',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1859,154,'8008533211',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1860,155,'8008533089/8008533160',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1861,156,'8008529862/8008530578',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1862,157,'8008535368/8008535468/8008535487/8008535525/8008535994','8008529892/8008533228/8008534371/8008534377',0);
INSERT INTO "vehicle_waybills" VALUES(1863,158,'8008530185/8008530191/8008533023/8008536066',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1864,159,'8008529892/8008533228/8008534371/8008534377',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1865,160,'8008536113/8008536115/8008536127',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1866,161,'8008531158/8008531210/8008532636/8008533110/8008533910',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1867,162,'8008536767/8008537643/8008538175/8008538640',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1868,163,'8008538166',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1869,164,'8008442881/8008527327',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1870,165,'8008469261',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1871,166,'8008540931/8008540932',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1872,167,'8008543131/8008543898/8008543909',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1873,168,'8008540875/8008542792/8008543064/8008543258',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1874,169,'8008532930/8008532964',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1875,170,'8008543768',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1876,171,'8008543544',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1877,172,'8008540882/8008543828','8008531120/8008531149/8008531166',0);
INSERT INTO "vehicle_waybills" VALUES(1878,173,'8008531120/8008531149/8008531166','-',0);
INSERT INTO "vehicle_waybills" VALUES(1879,174,'8008469244',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1880,175,'8008545002/8008546424',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1881,176,'8008547242/8008547248',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1882,177,'8008547163',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1883,178,'8008547052/8008547155/8008550526',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1884,179,'8008550754/8008550805',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1885,180,'8008547986/8008548011',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1886,181,'8008550492',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1887,182,'8008552215/8008552247/8008553573/8008553576/8008554471',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1888,183,'8008540620/8008540659/8008540668/8008552511',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1890,185,'8008544629/8008547193/8008547232/8008548428/8008554022/8008557482',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1891,186,'17061862',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1892,187,'8008546706/8008554791/8008555281/8008555779',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1893,188,'8008555971/8008555983/8008557797',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1894,189,'8008554736',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1895,190,'8008552221/8008554476/8008554481/8008554488/8008554492/8008555469/8008555972',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1896,191,'8008543546',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(1897,184,'8008550297',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2368,193,'8008501729/8008502144',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2369,194,'17056644',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2370,195,'8008488528',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2371,196,'8008498730/8008502166/8008504757',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2372,197,'17056777',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2373,198,'8008488531',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2374,199,'8008488530',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2375,200,'8008505170',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2376,201,'8008505960',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2377,202,'8008505270/8008508258',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2378,203,'8008496265/8008501544/8008501548/8008502023/8008504415/8008508297',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2379,204,'8008508594/8008508625/8008508626',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2380,205,'8008506031/8008506032/8008506375',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2381,206,'8008505351',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2382,207,'8008494308/8008502285/8008505956',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2383,208,'8008508905',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2384,209,'8008509621/8008510944',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2385,210,'8008488546',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2386,211,'8008509141',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2387,212,'8008488545',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2388,213,'8008488535/8008513662',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2389,214,'8008511318',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2390,215,'8008488542',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2391,216,'8008510761/8008513470',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2392,217,'8008510641/8008510647/8008510653/8008513120/8008513131/8008513466',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2393,218,'8008514702/8008515608',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2394,219,'8008480507/8008516142',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2395,220,'8008515545/8008515929',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2396,221,'8008501500/8008509617/8008514288/8008514392/8008514680',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2397,222,'84938085',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2398,223,'8008516713/8008518354',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2399,224,'8008517796',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2400,225,'17058956',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2401,226,'8008520547/8008520551/8008520554/8008520788/8008520874',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2402,227,'17059305',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2403,228,'8008520789/8008520790/8008520932',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2404,229,'8008519004',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2405,230,'8008421443',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2406,231,'8008521320',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2407,232,'8008519006',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2408,233,'8008519007/8008523521',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2409,234,'17057008',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2410,235,'8008518227/8008519145/8008520302/8008521255/8008521261/8008521269/8008523526',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2411,236,'8008524305/8008524310/8008524383/8008525699/8008526341/8008526595',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2412,237,'8008524127',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2413,238,'8008519012/8008525798',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2414,239,'8008520542/8008521306',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2415,240,'8008526383/8008526388/8008527817',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2416,241,'8008527673/8008527698',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2417,242,'8008524218/8008527777',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2418,243,'8008521887 8008525793 8008525795','8008521887/8008525793/8008525795',0);
INSERT INTO "vehicle_waybills" VALUES(2419,244,'8008529845/8008529847',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2420,245,'8008530107/8008530200',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2421,246,'8008532548/8008532588/8008533158/8008533349',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2422,247,'8008533375/8008533376',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2423,248,'8008532643/8008532887',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2424,249,'8008533211',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2425,250,'8008533089/8008533160',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2426,251,'8008529862/8008530578',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2427,252,'8008535368/8008535468/8008535487/8008535525/8008535994','8008529892/8008533228/8008534371/8008534377',0);
INSERT INTO "vehicle_waybills" VALUES(2428,253,'8008530185/8008530191/8008533023/8008536066',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2429,254,'8008529892/8008533228/8008534371/8008534377',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2430,255,'8008536113/8008536115/8008536127',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2431,256,'8008531158/8008531210/8008532636/8008533110/8008533910',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2432,257,'8008536767/8008537643/8008538175/8008538640',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2433,258,'8008538166',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2434,259,'8008442881/8008527327',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2435,260,'8008469261',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2436,261,'8008540931/8008540932',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2437,262,'8008543131/8008543898/8008543909',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2438,263,'8008540875/8008542792/8008543064/8008543258',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2439,264,'8008532930/8008532964',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2440,265,'8008543768',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2441,266,'8008543544',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2442,267,'8008540882/8008543828','8008531120/8008531149/8008531166',0);
INSERT INTO "vehicle_waybills" VALUES(2443,268,'8008531120/8008531149/8008531166','-',0);
INSERT INTO "vehicle_waybills" VALUES(2444,269,'8008469244',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2445,270,'8008545002/8008546424',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2446,271,'8008547242/8008547248',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2447,272,'8008547163',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2448,273,'8008547052/8008547155/8008550526',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2449,274,'8008550754/8008550805',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2450,275,'8008547986/8008548011',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2451,276,'8008550492',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2452,277,'8008552215/8008552247/8008553573/8008553576/8008554471',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2453,278,'8008540620/8008540659/8008540668/8008552511',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2454,279,'8008550297',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2455,280,'8008544629/8008547193/8008547232/8008548428/8008554022/8008557482',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2456,281,'17061862',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2457,282,'8008546706/8008554791/8008555281/8008555779',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2458,283,'8008555971/8008555983/8008557797',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2459,284,'8008554736',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2460,285,'8008552221/8008554476/8008554481/8008554488/8008554492/8008555469/8008555972',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(2461,286,'8008543546',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3496,287,'8008501729/8008502144',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3497,288,'17056644',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3498,289,'8008488528',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3499,290,'8008498730/8008502166/8008504757',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3500,291,'17056777',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3501,292,'8008488531',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3502,293,'8008488530',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3503,294,'8008505170',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3504,295,'8008505960',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3505,296,'8008505270/8008508258',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3506,297,'8008496265/8008501544/8008501548/8008502023/8008504415/8008508297',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3507,298,'8008508594/8008508625/8008508626',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3508,299,'8008506031/8008506032/8008506375',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3509,300,'8008505351',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3510,301,'8008494308/8008502285/8008505956',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3511,302,'8008508905',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3512,303,'8008509621/8008510944',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3513,304,'8008488546',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3514,305,'8008509141',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3515,306,'8008488545',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3516,307,'8008488535/8008513662',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3517,308,'8008511318',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3518,309,'8008488542',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3519,310,'8008510761/8008513470',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3520,311,'8008510641/8008510647/8008510653/8008513120/8008513131/8008513466',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3521,312,'8008514702/8008515608',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3522,313,'8008480507/8008516142',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3523,314,'8008515545/8008515929',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3524,315,'8008501500/8008509617/8008514288/8008514392/8008514680',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3525,316,'84938085',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3526,317,'8008516713/8008518354',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3527,318,'8008517796',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3528,319,'17058956',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3529,320,'8008520547/8008520551/8008520554/8008520788/8008520874',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3530,321,'17059305',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3531,322,'8008520789/8008520790/8008520932',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3532,323,'8008519004',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3533,324,'8008421443',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3534,325,'8008521320',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3535,326,'8008519006',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3536,327,'8008519007/8008523521',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3537,328,'17057008',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3538,329,'8008518227/8008519145/8008520302/8008521255/8008521261/8008521269/8008523526',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3539,330,'8008524305/8008524310/8008524383/8008525699/8008526341/8008526595',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3540,331,'8008524127',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3541,332,'8008519012/8008525798',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3542,333,'8008520542/8008521306',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3543,334,'8008526383/8008526388/8008527817',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3544,335,'8008527673/8008527698',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3545,336,'8008524218/8008527777',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3546,337,'8008521887 8008525793 8008525795','8008521887/8008525793/8008525795',0);
INSERT INTO "vehicle_waybills" VALUES(3547,338,'8008529845/8008529847',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3548,339,'8008530107/8008530200',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3549,340,'8008532548/8008532588/8008533158/8008533349',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3550,341,'8008533375/8008533376',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3551,342,'8008532643/8008532887',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3552,343,'8008533211',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3553,344,'8008533089/8008533160',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3554,345,'8008529862/8008530578',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3555,346,'8008535368/8008535468/8008535487/8008535525/8008535994','8008529892/8008533228/8008534371/8008534377',0);
INSERT INTO "vehicle_waybills" VALUES(3556,347,'8008530185/8008530191/8008533023/8008536066',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3557,348,'8008529892/8008533228/8008534371/8008534377',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3558,349,'8008536113/8008536115/8008536127',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3559,350,'8008531158/8008531210/8008532636/8008533110/8008533910',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3560,351,'8008536767/8008537643/8008538175/8008538640',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3561,352,'8008538166',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3562,353,'8008442881/8008527327',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3563,354,'8008469261',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3564,355,'8008540931/8008540932',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3565,356,'8008543131/8008543898/8008543909',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3566,357,'8008540875/8008542792/8008543064/8008543258',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3567,358,'8008532930/8008532964',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3568,359,'8008543768',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3569,360,'8008543544',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3570,361,'8008540882/8008543828','8008531120/8008531149/8008531166',0);
INSERT INTO "vehicle_waybills" VALUES(3571,362,'8008531120/8008531149/8008531166','-',0);
INSERT INTO "vehicle_waybills" VALUES(3572,363,'8008469244',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3573,364,'8008545002/8008546424',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3574,365,'8008547242/8008547248',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3575,366,'8008547163',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3576,367,'8008547052/8008547155/8008550526',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3577,368,'8008550754/8008550805',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3578,369,'8008547986/8008548011',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3579,370,'8008550492',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3580,371,'8008552215/8008552247/8008553573/8008553576/8008554471',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3581,372,'8008540620/8008540659/8008540668/8008552511',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3582,373,'8008550297',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3583,374,'8008544629/8008547193/8008547232/8008548428/8008554022/8008557482',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3584,375,'17061862',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3585,376,'8008546706/8008554791/8008555281/8008555779',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3586,377,'8008555971/8008555983/8008557797',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3587,378,'8008554736',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3588,379,'8008552221/8008554476/8008554481/8008554488/8008554492/8008555469/8008555972',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3589,380,'8008543546',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3778,382,'8008501729/8008502144',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3779,383,'17056644',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3780,384,'8008488528',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3781,385,'8008498730/8008502166/8008504757',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3782,386,'17056777',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3783,387,'8008488531',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3784,388,'8008488530',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3785,389,'8008505170',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3786,390,'8008505960',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3787,391,'8008505270/8008508258',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3788,392,'8008496265/8008501544/8008501548/8008502023/8008504415/8008508297',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3789,393,'8008508594/8008508625/8008508626',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3790,394,'8008506031/8008506032/8008506375',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3791,395,'8008505351',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3792,396,'8008494308/8008502285/8008505956',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3793,397,'8008508905',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3794,398,'8008509621/8008510944',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3795,399,'8008488546',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3796,400,'8008509141',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3797,401,'8008488545',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3798,402,'8008488535/8008513662',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3799,403,'8008511318',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3800,404,'8008488542',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3801,405,'8008510761/8008513470',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3802,406,'8008510641/8008510647/8008510653/8008513120/8008513131/8008513466',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3803,407,'8008514702/8008515608',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3804,408,'8008480507/8008516142',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3805,409,'8008515545/8008515929',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3806,410,'8008501500/8008509617/8008514288/8008514392/8008514680',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3807,411,'84938085',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3808,412,'8008516713/8008518354',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3809,413,'8008517796',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3810,414,'17058956',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3811,415,'8008520547/8008520551/8008520554/8008520788/8008520874',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3812,416,'17059305',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3813,417,'8008520789/8008520790/8008520932',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3814,418,'8008519004',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3815,419,'8008421443',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3816,420,'8008521320',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3817,421,'8008519006',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3818,422,'8008519007/8008523521',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3819,423,'17057008',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3820,424,'8008518227/8008519145/8008520302/8008521255/8008521261/8008521269/8008523526',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3821,425,'8008524305/8008524310/8008524383/8008525699/8008526341/8008526595',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3822,426,'8008524127',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3823,427,'8008519012/8008525798',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3824,428,'8008520542/8008521306',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3825,429,'8008526383/8008526388/8008527817',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3826,430,'8008527673/8008527698',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3827,431,'8008524218/8008527777',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3828,432,'8008521887 8008525793 8008525795','8008521887/8008525793/8008525795',0);
INSERT INTO "vehicle_waybills" VALUES(3829,433,'8008529845/8008529847',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3830,434,'8008530107/8008530200',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3831,435,'8008532548/8008532588/8008533158/8008533349',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3832,436,'8008533375/8008533376',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3833,437,'8008532643/8008532887',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3834,438,'8008533211',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3835,439,'8008533089/8008533160',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3836,440,'8008529862/8008530578',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3837,441,'8008535368/8008535468/8008535487/8008535525/8008535994','8008529892/8008533228/8008534371/8008534377',0);
INSERT INTO "vehicle_waybills" VALUES(3838,442,'8008530185/8008530191/8008533023/8008536066',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3839,443,'8008529892/8008533228/8008534371/8008534377',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3840,444,'8008536113/8008536115/8008536127',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3841,445,'8008531158/8008531210/8008532636/8008533110/8008533910',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3842,446,'8008536767/8008537643/8008538175/8008538640',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3843,447,'8008538166',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3844,448,'8008442881/8008527327',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3845,449,'8008469261',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3846,450,'8008540931/8008540932',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3847,451,'8008543131/8008543898/8008543909',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3848,452,'8008540875/8008542792/8008543064/8008543258',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3849,453,'8008532930/8008532964',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3850,454,'8008543768',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3851,455,'8008543544',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3852,456,'8008540882/8008543828','8008531120/8008531149/8008531166',0);
INSERT INTO "vehicle_waybills" VALUES(3853,457,'8008531120/8008531149/8008531166','-',0);
INSERT INTO "vehicle_waybills" VALUES(3854,458,'8008469244',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3855,459,'8008545002/8008546424',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3856,460,'8008547242/8008547248',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3857,461,'8008547163',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3858,462,'8008547052/8008547155/8008550526',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3859,463,'8008550754/8008550805',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3860,464,'8008547986/8008548011',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3861,465,'8008550492',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3862,466,'8008552215/8008552247/8008553573/8008553576/8008554471',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3863,467,'8008540620/8008540659/8008540668/8008552511',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3864,468,'8008550297',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3865,469,'8008544629/8008547193/8008547232/8008548428/8008554022/8008557482',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3866,470,'17061862',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3867,471,'8008546706/8008554791/8008555281/8008555779',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3868,472,'8008555971/8008555983/8008557797',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3869,473,'8008554736',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3870,474,'8008552221/8008554476/8008554481/8008554488/8008554492/8008555469/8008555972',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3871,475,'8008543546',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3872,479,'8008501729/8008502144',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3873,480,'17056644',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3874,481,'8008488528',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3875,482,'8008498730/8008502166/8008504757',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3876,483,'17056777',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3877,484,'8008488531',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3878,485,'8008488530',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3879,486,'8008505170',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3880,487,'8008505960',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3881,488,'8008505270/8008508258',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3882,489,'8008496265/8008501544/8008501548/8008502023/8008504415/8008508297',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3883,490,'8008508594/8008508625/8008508626',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3884,491,'8008506031/8008506032/8008506375',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3885,492,'8008505351',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3886,493,'8008494308/8008502285/8008505956',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3887,494,'8008508905',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3888,495,'8008509621/8008510944',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3889,496,'8008488546',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3890,497,'8008509141',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3891,498,'8008488545',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3892,499,'8008488535/8008513662',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3893,500,'8008511318',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3894,501,'8008488542',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3895,502,'8008510761/8008513470',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3896,503,'8008510641/8008510647/8008510653/8008513120/8008513131/8008513466',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3897,504,'8008514702/8008515608',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3898,505,'8008480507/8008516142',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3899,506,'8008515545/8008515929',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3900,507,'8008501500/8008509617/8008514288/8008514392/8008514680',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3901,508,'84938085',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3902,509,'8008516713/8008518354',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3903,510,'8008517796',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3904,511,'17058956',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3905,512,'8008520547/8008520551/8008520554/8008520788/8008520874',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3906,513,'17059305',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3907,514,'8008520789/8008520790/8008520932',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3908,515,'8008519004',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3909,516,'8008421443',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3910,517,'8008521320',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3911,518,'8008519006',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3912,519,'8008519007/8008523521',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3913,520,'17057008',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3914,521,'8008518227/8008519145/8008520302/8008521255/8008521261/8008521269/8008523526',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3915,522,'8008524305/8008524310/8008524383/8008525699/8008526341/8008526595',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3916,523,'8008524127',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3917,524,'8008519012/8008525798',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3918,525,'8008520542/8008521306',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3919,526,'8008526383/8008526388/8008527817',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3920,527,'8008527673/8008527698',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3921,528,'8008524218/8008527777',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3922,529,'8008521887 8008525793 8008525795','8008521887/8008525793/8008525795',0);
INSERT INTO "vehicle_waybills" VALUES(3923,530,'8008529845/8008529847',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3924,531,'8008530107/8008530200',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3925,532,'8008532548/8008532588/8008533158/8008533349',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3926,533,'8008533375/8008533376',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3927,534,'8008532643/8008532887',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3928,535,'8008533211',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3929,536,'8008533089/8008533160',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3930,537,'8008529862/8008530578',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3931,538,'8008535368/8008535468/8008535487/8008535525/8008535994','8008529892/8008533228/8008534371/8008534377',0);
INSERT INTO "vehicle_waybills" VALUES(3932,539,'8008530185/8008530191/8008533023/8008536066',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3933,540,'8008529892/8008533228/8008534371/8008534377',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3934,541,'8008536113/8008536115/8008536127',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3935,542,'8008531158/8008531210/8008532636/8008533110/8008533910',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3936,543,'8008536767/8008537643/8008538175/8008538640',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3937,544,'8008538166',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3938,545,'8008442881/8008527327',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3939,546,'8008469261',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3940,547,'8008540931/8008540932',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3941,548,'8008543131/8008543898/8008543909',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3942,549,'8008540875/8008542792/8008543064/8008543258',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3943,550,'8008532930/8008532964',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3944,551,'8008543768',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3945,552,'8008543544',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3946,553,'8008540882/8008543828','8008531120/8008531149/8008531166',0);
INSERT INTO "vehicle_waybills" VALUES(3947,554,'8008531120/8008531149/8008531166','-',0);
INSERT INTO "vehicle_waybills" VALUES(3948,555,'8008469244',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3949,556,'8008545002/8008546424',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3950,557,'8008547242/8008547248',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3951,558,'8008547163',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3952,559,'8008547052/8008547155/8008550526',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3953,560,'8008550754/8008550805',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3954,561,'8008547986/8008548011',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3955,562,'8008550492',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3956,563,'8008552215/8008552247/8008553573/8008553576/8008554471',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3957,564,'8008540620/8008540659/8008540668/8008552511',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3958,565,'8008550297',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3959,566,'8008544629/8008547193/8008547232/8008548428/8008554022/8008557482',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3960,567,'17061862',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3961,568,'8008546706/8008554791/8008555281/8008555779',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3962,569,'8008555971/8008555983/8008557797',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3963,570,'8008554736',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3964,571,'8008552221/8008554476/8008554481/8008554488/8008554492/8008555469/8008555972',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(3965,572,'8008543546',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4060,573,'8008501729/8008502144',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4061,574,'17056644',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4062,575,'8008488528',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4063,576,'8008498730/8008502166/8008504757',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4064,577,'17056777',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4065,578,'8008488531',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4066,579,'8008488530',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4067,580,'8008505170',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4068,581,'8008505960',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4069,582,'8008505270/8008508258',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4070,583,'8008496265/8008501544/8008501548/8008502023/8008504415/8008508297',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4071,584,'8008508594/8008508625/8008508626',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4072,585,'8008506031/8008506032/8008506375',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4073,586,'8008505351',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4074,587,'8008494308/8008502285/8008505956',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4075,588,'8008508905',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4076,589,'8008509621/8008510944',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4077,590,'8008488546',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4078,591,'8008509141',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4079,592,'8008488545',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4080,593,'8008488535/8008513662',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4081,594,'8008511318',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4082,595,'8008488542',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4083,596,'8008510761/8008513470',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4084,597,'8008510641/8008510647/8008510653/8008513120/8008513131/8008513466',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4085,598,'8008514702/8008515608',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4086,599,'8008480507/8008516142',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4087,600,'8008515545/8008515929',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4088,601,'8008501500/8008509617/8008514288/8008514392/8008514680',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4089,602,'84938085',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4090,603,'8008516713/8008518354',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4091,604,'8008517796',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4092,605,'17058956',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4093,606,'8008520547/8008520551/8008520554/8008520788/8008520874',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4094,607,'17059305',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4095,608,'8008520789/8008520790/8008520932',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4096,609,'8008519004',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4097,610,'8008421443',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4098,611,'8008521320',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4099,612,'8008519006',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4100,613,'8008519007/8008523521',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4101,614,'17057008',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4102,615,'8008518227/8008519145/8008520302/8008521255/8008521261/8008521269/8008523526',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4103,616,'8008524305/8008524310/8008524383/8008525699/8008526341/8008526595',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4104,617,'8008524127',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4105,618,'8008519012/8008525798',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4106,619,'8008520542/8008521306',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4107,620,'8008526383/8008526388/8008527817',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4108,621,'8008527673/8008527698',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4109,622,'8008524218/8008527777',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4110,623,'8008521887 8008525793 8008525795','8008521887/8008525793/8008525795',0);
INSERT INTO "vehicle_waybills" VALUES(4111,624,'8008529845/8008529847',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4112,625,'8008530107/8008530200',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4113,626,'8008532548/8008532588/8008533158/8008533349',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4114,627,'8008533375/8008533376',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4115,628,'8008532643/8008532887',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4116,629,'8008533211',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4117,630,'8008533089/8008533160',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4118,631,'8008529862/8008530578',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4119,632,'8008535368/8008535468/8008535487/8008535525/8008535994','8008529892/8008533228/8008534371/8008534377',0);
INSERT INTO "vehicle_waybills" VALUES(4120,633,'8008530185/8008530191/8008533023/8008536066',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4121,634,'8008529892/8008533228/8008534371/8008534377',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4122,635,'8008536113/8008536115/8008536127',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4123,636,'8008531158/8008531210/8008532636/8008533110/8008533910',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4124,637,'8008536767/8008537643/8008538175/8008538640',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4125,638,'8008538166',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4126,639,'8008442881/8008527327',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4127,640,'8008469261',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4128,641,'8008540931/8008540932',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4129,642,'8008543131/8008543898/8008543909',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4130,643,'8008540875/8008542792/8008543064/8008543258',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4131,644,'8008532930/8008532964',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4132,645,'8008543768',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4133,646,'8008543544',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4134,647,'8008540882/8008543828','8008531120/8008531149/8008531166',0);
INSERT INTO "vehicle_waybills" VALUES(4135,648,'8008531120/8008531149/8008531166','-',0);
INSERT INTO "vehicle_waybills" VALUES(4136,649,'8008469244',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4137,650,'8008545002/8008546424',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4138,651,'8008547242/8008547248',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4139,652,'8008547163',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4140,653,'8008547052/8008547155/8008550526',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4141,654,'8008550754/8008550805',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4142,655,'8008547986/8008548011',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4143,656,'8008550492',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4144,657,'8008552215/8008552247/8008553573/8008553576/8008554471',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4145,658,'8008540620/8008540659/8008540668/8008552511',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4146,659,'8008550297',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4147,660,'8008544629/8008547193/8008547232/8008548428/8008554022/8008557482',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4148,661,'17061862',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4149,662,'8008546706/8008554791/8008555281/8008555779',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4150,663,'8008555971/8008555983/8008557797',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4151,664,'8008554736',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4152,665,'8008552221/8008554476/8008554481/8008554488/8008554492/8008555469/8008555972',NULL,0);
INSERT INTO "vehicle_waybills" VALUES(4153,666,'8008543546',NULL,0);
CREATE TABLE warehouse_staff_position_versions (
	id INTEGER NOT NULL, 
	position_id INTEGER NOT NULL, 
	warehouse_id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	monthly_rate NUMERIC(18, 2) DEFAULT '0' NOT NULL, 
	headcount SMALLINT DEFAULT '1' NOT NULL, 
	valid_from DATE NOT NULL, 
	valid_to DATE, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(position_id) REFERENCES warehouse_staff_positions (id) ON DELETE CASCADE, 
	FOREIGN KEY(warehouse_id) REFERENCES warehouses (id) ON DELETE CASCADE, 
	CONSTRAINT ck_staff_pos_versions_dates CHECK (valid_to IS NULL OR valid_to >= valid_from)
);
CREATE TABLE warehouse_staff_positions (
	id INTEGER NOT NULL, 
	warehouse_id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	monthly_rate NUMERIC(18, 2) DEFAULT '0' NOT NULL, 
	headcount SMALLINT DEFAULT '1' NOT NULL, 
	is_active BOOLEAN DEFAULT 1 NOT NULL, 
	sort_order INTEGER DEFAULT '0' NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(warehouse_id) REFERENCES warehouses (id) ON DELETE CASCADE, 
	CONSTRAINT ck_staff_positions_headcount CHECK (headcount > 0)
);
CREATE TABLE warehouses (
	id INTEGER NOT NULL, 
	code VARCHAR(32) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	security_visit_place VARCHAR(64), 
	is_active BOOLEAN DEFAULT 1 NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (code)
);
INSERT INTO "warehouses" VALUES(2,'strelna','Стрельна','Склад ГП',1,'2026-09-02 04:33:31.335920','2026-09-02 10:43:47.775017');
CREATE INDEX ix_vehicle_operations_wh_date ON vehicle_operations (warehouse_id, operation_date);
CREATE INDEX ix_operation_daily_totals_wh_date ON operation_daily_totals (warehouse_id, report_date);
CREATE INDEX ix_shift_day_confirm_wh_date ON shift_day_confirmations (warehouse_id, report_date);
CREATE INDEX ix_vehicle_waybills_op ON vehicle_waybills (vehicle_operation_id, sort_order);
CREATE INDEX ix_billing_periods_contract_ym ON billing_periods (contract_id, period_year, period_month);
CREATE INDEX ix_staff_positions_wh ON warehouse_staff_positions (warehouse_id, sort_order);
CREATE INDEX ix_staff_pos_versions_wh_dates ON warehouse_staff_position_versions (warehouse_id, valid_from, valid_to);
COMMIT;
