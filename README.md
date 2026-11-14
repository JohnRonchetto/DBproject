# Rental Store Database

A command-line rental management system in **Python** and **MariaDB**. Staff can rent
and return items, grant extensions, manage a first-come-first-served waitlist, and
search customers, items and rental records.

It runs on real-scale data from the **TPC-DS** retail benchmark: about 18,000 items,
100,000 customers and 2.7 million past rentals built from historical sales.

## Features

- **Rent and return:** 14-day rentals. Returned items move to rental history with the return date.
- **Extensions:** one 14-day extension per rental.
- **Waitlist:** when an item is out of stock, customers can join a queue. Only the person
  at the front of the line can rent it when a copy comes back.
- **Search:** filter items, customers, rentals, rental history and the waitlist by any
  field, with optional pattern matching (SQL `LIKE`), price ranges and year ranges.
- **Manage records:** add items and customers, and edit customer details.

All queries use parameterized statements, so user input is never inserted directly into SQL.

## Database schema

| Table | Contents |
|---|---|
| `item` | Products from TPC-DS, plus how many copies the store owns |
| `customer`, `customer_address` | Customers and their addresses from TPC-DS |
| `store_sales`, `date_dim` | Historical sales and dates, used to build rental history |
| `rental` | Items currently checked out, with due dates |
| `rental_history` | Completed rentals with return dates |
| `waitlist` | Customers waiting for an item, with their place in line |

## Setup

Requires Python 3.10+ and a running MariaDB server.

1. Install the MariaDB connector:
   ```bash
   pip install mariadb
   ```
2. Copy `MARIADB_CREDS_example.py` to `MARIADB_CREDS.py` and fill in your database login.
   `MARIADB_CREDS.py` is in `.gitignore`, so your password stays private.
3. Create the tables and load the data (takes a few minutes):
   ```bash
   python setup_db.py
   ```
4. Start the app:
   ```bash
   python main.py
   ```

```
What would you like to do?
1. Rent an Item
2. Return an Item
3. Grant an Extension
4. Search a Table
5. Add an Item
6. Add a Customer
7. Edit a Customer
8. Exit
```

## Tests

`public_tests.py` has 17 unit tests for the database layer. One of them,
`test_close_connection`, closes the shared connection, so run tests one at a time:

```bash
python -m unittest public_tests.PublicTests.test_rent_item
```

## Project structure

```
main.py                   menu loop
helper_functions.py       menus, input validation and rental rules
db_handler.py             all SQL queries
setup_db.py               creates tables and loads the TPC-DS data
models/                   Item, Customer, Rental, RentalHistory, Waitlist classes
tpcds_data/               TPC-DS CSV files
public_tests.py           unit tests
MARIADB_CREDS_example.py  template for database credentials
```

Built for a database course.
