from MARIADB_CREDS import DB_CONFIG
from mariadb import connect
from models.RentalHistory import RentalHistory
from models.Waitlist import Waitlist
from models.Item import Item
from models.Rental import Rental
from models.Customer import Customer
from datetime import date, timedelta


conn = connect(user=DB_CONFIG["username"], password=DB_CONFIG["password"], host=DB_CONFIG["host"],
               database=DB_CONFIG["database"], port=DB_CONFIG["port"])


cur = conn.cursor()


def add_item(new_item: Item = None):
    """
    new_item - An Item object containing a new item to be inserted into the DB in the item table.
        new_item and its attributes will never be None.
    """

    cur.execute("SELECT MAX(i_item_sk) FROM item")
    # or 0 handles edge case of empty table where MAX returns None
    new_sk = (cur.fetchone()[0] or 0) + 1

    cur.execute(
        "INSERT INTO item (i_item_sk, i_item_id, i_rec_start_date, i_product_name, i_brand, "
        "i_category, i_manufact, i_current_price, i_num_owned) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (new_sk, new_item.item_id, f"{new_item.start_year}-01-01",
         new_item.product_name, new_item.brand, new_item.category,
         new_item.manufact, new_item.current_price, new_item.num_owned)
    )


def add_customer(new_customer: Customer = None):
    """
    new_customer - A Customer object containing a new customer to be inserted into the DB in the customer table.
        new_customer and its attributes will never be None.
    """

    # Parse street_number, street_name, city, state, and zip_code
    parts = new_customer.address.split(', ')
    street_number, street_name = parts[0].split(' ', 1)
    city = parts[1]
    state, zip_code = parts[2].split(' ', 1)

    cur.execute("SELECT MAX(ca_address_sk) FROM customer_address")
    new_addr_sk = (cur.fetchone()[0] or 0) + 1
    cur.execute(
        "INSERT INTO customer_address (ca_address_sk, ca_street_number, ca_street_name, ca_city, ca_state, ca_zip) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (new_addr_sk, street_number, street_name, city, state, zip_code)
    )

    name_parts = new_customer.name.split(' ', 1)
    first_name = name_parts[0]
    # handle edge case of single word name with no last name
    last_name = name_parts[1] if len(name_parts) > 1 else '' 

    cur.execute("SELECT MAX(c_customer_sk) FROM customer")
    new_cust_sk = (cur.fetchone()[0] or 0) + 1
    cur.execute(
        "INSERT INTO customer (c_customer_sk, c_customer_id, c_first_name, c_last_name, c_email_address, c_current_addr_sk) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (new_cust_sk, new_customer.customer_id, first_name, last_name, new_customer.email, new_addr_sk)
    )


def edit_customer(original_customer_id: str = None, new_customer: Customer = None):
    """
    original_customer_id - A string containing the customer id for the customer to be edited.
    new_customer - A Customer object containing attributes to update. If an attribute is None, it should not be altered.
    """
    # Fetch surrogate keys once so we can use them for all updates below
    cur.execute(
        "SELECT c_customer_sk, c_current_addr_sk FROM customer WHERE c_customer_id = ?",
        (original_customer_id,)
    )
    cust_sk, addr_sk = cur.fetchone()

    if new_customer.name is not None:
        name_parts = new_customer.name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        cur.execute(
            "UPDATE customer SET c_first_name = ?, c_last_name = ? WHERE c_customer_sk = ?",
            (first_name, last_name, cust_sk)
        )

    if new_customer.email is not None:
        cur.execute(
            "UPDATE customer SET c_email_address = ? WHERE c_customer_sk = ?",
            (new_customer.email, cust_sk)
        )

    # Update customer_id last so original_customer_id stays valid for lookups above
    if new_customer.customer_id is not None:
        cur.execute(
            "UPDATE customer SET c_customer_id = ? WHERE c_customer_sk = ?",
            (new_customer.customer_id, cust_sk)
        )

    if new_customer.address is not None:
        parts = new_customer.address.split(', ')
        street_number, street_name = parts[0].split(' ', 1)
        city = parts[1]
        state, zip_code = parts[2].split(' ', 1)
        cur.execute(
            "UPDATE customer_address "
            "SET ca_street_number = ?, ca_street_name = ?, ca_city = ?, ca_state = ?, ca_zip = ? "
            "WHERE ca_address_sk = ?",
            (street_number, street_name, city, state, zip_code, addr_sk)
        )


def rent_item(item_id: str = None, customer_id: str = None):
    """
    item_id - A string containing the Item ID for the item being rented.
    customer_id - A string containing the customer id of the customer renting the item.
    """
    today = date.today()
    due = today + timedelta(days=14)
    cur.execute(
        "INSERT INTO rental (item_id, customer_id, rental_date, due_date) VALUES (?, ?, ?, ?)",
        (item_id, customer_id, str(today), str(due))
    )


def waitlist_customer(item_id: str = None, customer_id: str = None) -> int:
    """
    Returns the customer's new place in line.
    """
    raise NotImplementedError("you must implement this function")

def update_waitlist(item_id: str = None):
    """
    Removes person at position 1 and shifts everyone else down by 1.
    """
    raise NotImplementedError("you must implement this function")


def return_item(item_id: str = None, customer_id: str = None):
    """
    Moves a rental from rental to rental_history with return_date = today.
    """
    raise NotImplementedError("you must implement this function")


def grant_extension(item_id: str = None, customer_id: str = None):
    """
    Adds 14 days to the due_date.
    """
    raise NotImplementedError("you must implement this function")


def get_filtered_items(filter_attributes: Item = None,
                       use_patterns: bool = False,
                       min_price: float = -1,
                       max_price: float = -1,
                       min_start_year: int = -1,
                       max_start_year: int = -1) -> list[Item]:
    """
    Returns a list of Item objects matching the filters.
    """
    raise NotImplementedError("you must implement this function")


def get_filtered_customers(filter_attributes: Customer = None, use_patterns: bool = False) -> list[Customer]:
    """
    Returns a list of Customer objects matching the filters.
    """
    raise NotImplementedError("you must implement this function")


def get_filtered_rentals(filter_attributes: Rental = None,
                         min_rental_date: str = None,
                         max_rental_date: str = None,
                         min_due_date: str = None,
                         max_due_date: str = None) -> list[Rental]:
    """
    Returns a list of Rental objects matching the filters.
    """
    raise NotImplementedError("you must implement this function")


def get_filtered_rental_histories(filter_attributes: RentalHistory = None,
                                  min_rental_date: str = None,
                                  max_rental_date: str = None,
                                  min_due_date: str = None,
                                  max_due_date: str = None,
                                  min_return_date: str = None,
                                  max_return_date: str = None) -> list[RentalHistory]:
    """
    Returns a list of RentalHistory objects matching the filters.
    """
    raise NotImplementedError("you must implement this function")


def get_filtered_waitlist(filter_attributes: Waitlist = None,
                          min_place_in_line: int = -1,
                          max_place_in_line: int = -1) -> list[Waitlist]:
    """
    Returns a list of Waitlist objects matching the filters.
    """
    raise NotImplementedError("you must implement this function")


def number_in_stock(item_id: str = None) -> int:
    """
    Returns num_owned - active rentals. Returns -1 if item doesn't exist.
    """
    raise NotImplementedError("you must implement this function")


def place_in_line(item_id: str = None, customer_id: str = None) -> int:
    """
    Returns the customer's place_in_line, or -1 if not on waitlist.
    """
    raise NotImplementedError("you must implement this function")


def line_length(item_id: str = None) -> int:
    """
    Returns how many people are on the waitlist for this item.
    """
    raise NotImplementedError("you must implement this function")


def save_changes():
    """
    Commits all changes made to the db.
    """
    raise NotImplementedError("you must implement this function")


def close_connection():
    """
    Closes the cursor and connection.
    """
    raise NotImplementedError("you must implement this function")

