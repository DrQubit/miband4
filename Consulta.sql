SELECT record_timestamp,hr.hr FROM hr WHERE mac!="C0:63:64:53:34:E2" AND hr.hr>0 AND record_timestamp>"2021-04-26 07:00:00" ORDER BY record_timestamp LIMIT 1000;
