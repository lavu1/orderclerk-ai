-- Fictional shop; prices in integer ZMW minor units.
INSERT OR IGNORE INTO customers (id,display_name) VALUES (1,'Demo Customer');
INSERT OR IGNORE INTO products (id,sku,name,unit,price_minor) VALUES
 (1,'RICE-2KG','Rice 2kg','bag',5500),
 (2,'OIL-1L','Cooking oil 1L','bottle',4500);
INSERT OR IGNORE INTO product_aliases (alias,product_id) VALUES
 ('rice',1),('rice 2kg',1),('2kg rice',1),
 ('oil',2),('cooking oil',2),('cooking oil 1l',2),('1l oil',2);
INSERT OR IGNORE INTO stock_movements (id,product_id,quantity_delta,reason) VALUES
 (1,1,10,'opening'),(2,2,3,'opening');
