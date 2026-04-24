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
    new_place = line_length(item_id) + 1
    cur.execute(
        "INSERT INTO waitlist (item_id, customer_id, place_in_line) VALUES (?, ?, ?)",
        (item_id, customer_id, new_place)
    )
    return new_place

def update_waitlist(item_id: str = None):
    """
    Removes person at position 1 and shifts everyone else down by 1.
    """
    cur.execute(
        "DELETE FROM waitlist WHERE item_id = ? AND place_in_line = 1",
        (item_id,)
    )
    cur.execute(
        "UPDATE waitlist SET place_in_line = place_in_line - 1 WHERE item_id = ?",
        (item_id,)
    )


def return_item(item_id: str = None, customer_id: str = None):
    """
    Moves a rental from rental to rental_history with return_date = today.
    """
    cur.execute(
        "SELECT rental_date, due_date FROM rental WHERE item_id = ? AND customer_id = ?",
        (item_id, customer_id)
    )
    rental_date, due_date = cur.fetchone()

    cur.execute(
        "INSERT INTO rental_history (item_id, customer_id, rental_date, due_date, return_date) "
        "VALUES (?, ?, ?, ?, ?)",
        (item_id, customer_id, rental_date, due_date, str(date.today()))
    )
    cur.execute(
        "DELETE FROM rental WHERE item_id = ? AND customer_id = ?",
        (item_id, customer_id)
    )


def grant_extension(item_id: str = None, customer_id: str = None):
    """
    Adds 14 days to the due_date.
    """
    # Note that the helper_function.py already checks for max 28 day extention.
    # Also use DATE_ADD(), which is cleaner than getting date though python
    cur.execute(
        "UPDATE rental SET due_date = DATE_ADD(due_date, INTERVAL 14 DAY) "
        "WHERE item_id = ? AND customer_id = ?",
        (item_id, customer_id)
    )


def get_filtered_items(filter_attributes: Item = None,
                       use_patterns: bool = False,
                       min_price: float = -1,
                       max_price: float = -1,
                       min_start_year: int = -1,
                       max_start_year: int = -1) -> list[Item]:
    """
    Returns a list of Item objects matching the filters.
    """
    # Use TRIM() which strips trailing spaces from CHAR columns
    # WHERE 1=1 lets safely append AND clauses without special casing the first condition
    query = (
        "SELECT TRIM(i_item_id), TRIM(i_product_name), TRIM(i_brand), TRIM(i_category), "
        "TRIM(i_manufact), i_current_price, YEAR(i_rec_start_date), i_num_owned "
        "FROM item WHERE 1=1"
    )
    params = []

    # Apply LIKE/= pattern filters from filter_attributes if provided
    if filter_attributes is not None:
        op = "LIKE" if use_patterns else "="

        if filter_attributes.item_id is not None:
            query += f" AND i_item_id {op} ?"
            params.append(filter_attributes.item_id)
        if filter_attributes.product_name is not None:
            query += f" AND i_product_name {op} ?"
            params.append(filter_attributes.product_name)
        if filter_attributes.brand is not None:
            query += f" AND i_brand {op} ?"
            params.append(filter_attributes.brand)
        if filter_attributes.category is not None:
            query += f" AND i_category {op} ?"
            params.append(filter_attributes.category)
        if filter_attributes.manufact is not None:
            query += f" AND i_manufact {op} ?"
            params.append(filter_attributes.manufact)
        if filter_attributes.current_price != -1:
            query += " AND i_current_price = ?"
            params.append(filter_attributes.current_price)
        if filter_attributes.num_owned != -1:
            query += " AND i_num_owned = ?"
            params.append(filter_attributes.num_owned)
        if filter_attributes.start_year != -1:
            query += " AND YEAR(i_rec_start_date) = ?"
            params.append(filter_attributes.start_year)

    # Apply inclusive range filters (-1 means not provided, so skip)
    if min_price != -1:
        query += " AND i_current_price >= ?"
        params.append(min_price)
    if max_price != -1:
        query += " AND i_current_price <= ?"
        params.append(max_price)
    if min_start_year != -1:
        query += " AND YEAR(i_rec_start_date) >= ?"
        params.append(min_start_year)
    if max_start_year != -1:
        query += " AND YEAR(i_rec_start_date) <= ?"
        params.append(max_start_year)

    cur.execute(query, params)
    rows = cur.fetchall()

    # Return list of Item from the query results
    items = []
    for r in rows:
        item = Item(
            item_id=r[0],
            product_name=r[1],
            brand=r[2],
            category=r[3],
            manufact=r[4],
            current_price=r[5],
            start_year=r[6],
            num_owned=r[7]
        )
        items.append(item)
    return items


def get_filtered_customers(filter_attributes: Customer = None, use_patterns: bool = False) -> list[Customer]:
    """
    Returns a list of Customer objects matching the filters.
    """
    # Name lives in two columns, address lives across five columns in a separate table
    # CONCAT + TRIM assembles them into the format the Customer model expects
    # LEFT JOIN so customers without an address still appear
    query = (
        "SELECT TRIM(c.c_customer_id), "
        "CONCAT(TRIM(c.c_first_name), ' ', TRIM(c.c_last_name)), "
        "CONCAT(TRIM(ca.ca_street_number), ' ', TRIM(ca.ca_street_name), ', ', "
        "TRIM(ca.ca_city), ', ', TRIM(ca.ca_state), ' ', TRIM(ca.ca_zip)), "
        "TRIM(c.c_email_address) "
        "FROM customer c "
        "LEFT JOIN customer_address ca ON c.c_current_addr_sk = ca.ca_address_sk "
        "WHERE 1=1"
    )
    params = []

    if filter_attributes is not None:
        op = "LIKE" if use_patterns else "="

        if filter_attributes.customer_id is not None:
            query += f" AND c.c_customer_id {op} ?"
            params.append(filter_attributes.customer_id)
        # Filter on the assembled full name
        if filter_attributes.name is not None:
            query += f" AND CONCAT(TRIM(c.c_first_name), ' ', TRIM(c.c_last_name)) {op} ?"
            params.append(filter_attributes.name)
        # Filter on the assembled full address
        if filter_attributes.address is not None:
            query += (
                f" AND CONCAT(TRIM(ca.ca_street_number), ' ', TRIM(ca.ca_street_name), ', ', "
                f"TRIM(ca.ca_city), ', ', TRIM(ca.ca_state), ' ', TRIM(ca.ca_zip)) {op} ?"
            )
            params.append(filter_attributes.address)
        if filter_attributes.email is not None:
            query += f" AND c.c_email_address {op} ?"
            params.append(filter_attributes.email)

    cur.execute(query, params)
    rows = cur.fetchall()

    customers = []
    for r in rows:
        customer = Customer(
            customer_id=r[0],
            name=r[1],
            address=r[2],
            email=r[3]
        )
        customers.append(customer)
    return customers


def get_filtered_rentals(filter_attributes: Rental = None,
                         min_rental_date: str = None,
                         max_rental_date: str = None,
                         min_due_date: str = None,
                         max_due_date: str = None) -> list[Rental]:
    """
    Returns a list of Rental objects matching the filters.
    """

    query = (
        "SELECT TRIM(item_id), TRIM(customer_id), rental_date, due_date "
        "FROM rental WHERE 1=1"
    )
    params = []

    # Apply = filters from filter_attributes if provided
    if filter_attributes is not None:
        if filter_attributes.item_id is not None:
            query += " AND item_id = ?"
            params.append(filter_attributes.item_id)
        if filter_attributes.customer_id is not None:
            query += " AND customer_id = ?"
            params.append(filter_attributes.customer_id)
        if filter_attributes.rental_date is not None:
            query += " AND rental_date = ?"
            params.append(filter_attributes.rental_date)
        if filter_attributes.due_date is not None:
            query += " AND due_date = ?"
            params.append(filter_attributes.due_date)

    # Apply inclusive date range filters 
    if min_rental_date is not None:
        query += " AND rental_date >= ?"
        params.append(min_rental_date)
    if max_rental_date is not None:
        query += " AND rental_date <= ?"
        params.append(max_rental_date)
    if min_due_date is not None:
        query += " AND due_date >= ?"
        params.append(min_due_date)
    if max_due_date is not None:
        query += " AND due_date <= ?"
        params.append(max_due_date)

    cur.execute(query, params)
    rows = cur.fetchall()

    rentals = []
    for r in rows:
        rental = Rental(
            item_id=r[0],
            customer_id=r[1],
            rental_date=str(r[2]),
            due_date=str(r[3])
        )
        rentals.append(rental)
    return rentals


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

    query = (
        "SELECT TRIM(item_id), TRIM(customer_id), rental_date, due_date, return_date "
        "FROM rental_history WHERE 1=1"
    )
    params = []

    # Apply = filters from filter_attributes if provided
    if filter_attributes is not None:
        if filter_attributes.item_id is not None:
            query += " AND item_id = ?"
            params.append(filter_attributes.item_id)
        if filter_attributes.customer_id is not None:
            query += " AND customer_id = ?"
            params.append(filter_attributes.customer_id)
        if filter_attributes.rental_date is not None:
            query += " AND rental_date = ?"
            params.append(filter_attributes.rental_date)
        if filter_attributes.due_date is not None:
            query += " AND due_date = ?"
            params.append(filter_attributes.due_date)
        if filter_attributes.return_date is not None:
            query += " AND return_date = ?"
            params.append(filter_attributes.return_date)

    # Apply inclusive date range filters
    if min_rental_date is not None:
        query += " AND rental_date >= ?"
        params.append(min_rental_date)
    if max_rental_date is not None:
        query += " AND rental_date <= ?"
        params.append(max_rental_date)
    if min_due_date is not None:
        query += " AND due_date >= ?"
        params.append(min_due_date)
    if max_due_date is not None:
        query += " AND due_date <= ?"
        params.append(max_due_date)
    if min_return_date is not None:
        query += " AND return_date >= ?"
        params.append(min_return_date)
    if max_return_date is not None:
        query += " AND return_date <= ?"
        params.append(max_return_date)

    cur.execute(query, params)
    rows = cur.fetchall()

    histories = []
    for r in rows:
        history = RentalHistory(
            item_id=r[0],
            customer_id=r[1],
            rental_date=str(r[2]),
            due_date=str(r[3]),
            return_date=str(r[4])
        )
        histories.append(history)
    return histories


def get_filtered_waitlist(filter_attributes: Waitlist = None,
                          min_place_in_line: int = -1,
                          max_place_in_line: int = -1) -> list[Waitlist]:
    """
    Returns a list of Waitlist objects matching the filters.
    """

    query = (
        "SELECT TRIM(item_id), TRIM(customer_id), place_in_line "
        "FROM waitlist WHERE 1=1"
    )
    params = []

    # Apply filters from filter_attributes if provided
    if filter_attributes is not None:
        if filter_attributes.item_id is not None:
            query += " AND item_id = ?"
            params.append(filter_attributes.item_id)
        if filter_attributes.customer_id is not None:
            query += " AND customer_id = ?"
            params.append(filter_attributes.customer_id)
        # place_in_line uses -1 as the "not provided", since it's an integer
        if filter_attributes.place_in_line != -1:
            query += " AND place_in_line = ?"
            params.append(filter_attributes.place_in_line)

    # Apply inclusive range filters
    if min_place_in_line != -1:
        query += " AND place_in_line >= ?"
        params.append(min_place_in_line)
    if max_place_in_line != -1:
        query += " AND place_in_line <= ?"
        params.append(max_place_in_line)

    cur.execute(query, params)
    rows = cur.fetchall()

    waitlist_entries = []
    for r in rows:
        entry = Waitlist(
            item_id=r[0],
            customer_id=r[1],
            place_in_line=r[2]
        )
        waitlist_entries.append(entry)
    return waitlist_entries


def number_in_stock(item_id: str = None) -> int:
    """
    Returns num_owned - active rentals. Returns -1 if item doesn't exist.
    """

    cur.execute("SELECT i_num_owned FROM item WHERE i_item_id = ?", (item_id,))
    row = cur.fetchone()

    # Return -1 if the item doesn't exist
    if row is None:
        return -1

    num_owned = row[0]

    # Count how many copies are currently checked out
    cur.execute("SELECT COUNT(*) FROM rental WHERE item_id = ?", (item_id,))
    active_rentals = cur.fetchone()[0]

    return num_owned - active_rentals


def place_in_line(item_id: str = None, customer_id: str = None) -> int:
    """
    Returns the customer's place_in_line, or -1 if not on waitlist.
    """
    
    cur.execute(
        "SELECT place_in_line FROM waitlist WHERE item_id = ? AND customer_id = ?",
        (item_id, customer_id)
    )
    row = cur.fetchone()

    # Return -1 if the customer is not on the waitlist for this item
    if row is None:
        return -1

    return row[0]


def line_length(item_id: str = None) -> int:
    """
    Returns how many people are on the waitlist for this item.
    """
    cur.execute("SELECT COUNT(*) FROM waitlist WHERE item_id = ?", (item_id,))
    return cur.fetchone()[0]


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

