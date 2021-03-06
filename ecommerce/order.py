import datetime
import products
import random
import sqlite3
from typing import Any
from uuid import UUID, uuid4


def formatCentsToDollars(cents: int) -> str:
    """Takes in an arbitrary amount of cents; returns that amount of cents
    as a string formatted as \"$<dollars>.<cents>\"."""
    temp = str(cents)
    negative = bool()
    if cents < 0:
        temp = temp[1:]  # remove negative sign
        cents = abs(cents)
        negative = True

    if cents < 10:
        temp = "$0.0" + temp
    elif cents < 100:
        temp = "$0." + temp
    else:
        temp = "$" + temp[:-2] + "." + temp[-2:]
    return temp if not negative else f"-{temp}"


#! Research whether it would be best to merge products.db and discounts.db into a single database,
#! just with multiple tables. In the future, we will also want a orders database as well, so consider that.

DISCOUNTS_DATABASE = "discounts.db"
"""Database represented with columns 
- discountCode: text
- percentage: integer
- dollarAmt: integer
- freeShipping: boolean
- expirationDateTime: datetime

`discountCode` is the primary key, and therefore must be unique.

Each discount code corresponds to a certain type of discount. Each discount can 
represent only one of the following:
- A specific percentage off the order total
- A specific dollar amount subtracted from the order total
- Free shipping
Thus, for whichever type of discount is set, the other two must be marked `NULL`.

Each discount code can also be set to expire after a certain date and time. For 
a never-expiring discount code, set this value to `NULL`.
"""

# TODO: Figure out if we should use datetime or text type for storing expirationDate.
#! datetime would be nice because then sqlite can use ORDER BY statements internally.
#! As such, though, what format does the data go in as? How can I input it from the output of datetime.isoformat(),
#! and output it to construct a datetime object (presumably using datetime.fromisoformat())?
#! Also, are union types allowed; i.e., can datetime be NULL *or* datetime? Otherwise, we will need to designate
#! a specific time, like 0,0,0,0,0 to mean "this code never expires"
def initDiscountDatabase() -> None:
    """Create the discounts database. Only intended to be run once."""
    response = input(
        f"""Are you sure you want to create a new table?\nThis may overwrite an existing {DISCOUNTS_DATABASE} if it already exists. [y/n]: """
    )
    while True:
        if response[0].lower() == "y":
            con = sqlite3.connect(DISCOUNTS_DATABASE)
            cur = con.cursor()
            cur.execute(
                "CREATE TABLE discounts (discountCode text, percentage integer, dollarAmt integer, freeShipping boolean, expirationDateTime datetime)"
            )
            con.commit()
            con.close()
            break
        elif response[0].lower() == "n":
            break
        else:
            response = input("Please enter [y/n]: ")


def _check_add_discount_args(
    arg0: Any | None, arg1: Any | None, arg2: Any | None
) -> bool:
    """Returns `False` only when exactly one of the arguments is not `None`."""
    if (
        # if 0 arguments are set
        (arg0 is None and arg1 is None and arg2 is None)
        # if 2 arguments are set
        or (arg0 is None and arg1 is not None and arg2 is not None)
        or (arg0 is not None and arg1 is not None and arg2 is None)
        or (arg0 is not None and arg1 is None and arg2 is not None)
        # if 3 arguments are set
        or (arg0 is not None and arg1 is not None and arg2 is not None)
    ):
        return True
    else:
        # if 1 argument is set
        return False


def addDiscountToDatabase(
    discountCode: str,
    percentage: int | None = None,
    dollarAmt: int | None = None,
    freeShipping: bool | None = None,
    expirationDate: datetime.datetime | None = None,
) -> None:
    """Add a discount code to the database.

    Each discount code needs some method of discounting, so exactly one of
    `percentage`, `dollarAmt`, or `freeShipping` must not be `None`. If this
    is violated, a sqlite3.ProgrammingError is raised.

    - `percentage` must be `None` or an integer on the interval [1,100]. If it
    isn't, a ValueError is raised.
    - `dollarAmt` must be `None` or a positive integer. If it isn't, a
    ValueError is raised.

    If `expirationDate` is `None`, the discount code never expires unless the
    database entry is modified in the future.
    """

    if _check_add_discount_args(percentage, dollarAmt, freeShipping):
        raise sqlite3.ProgrammingError(
            "Exactly one of `percentage`, `dollarAmt`, or `freeShipping` must not be `None`."
        )

    if percentage is not None and (percentage < 1 or percentage > 100):
        raise ValueError("`percentage` must be on the interval [1,100].")

    if dollarAmt is not None and dollarAmt < 1:
        raise ValueError("`dollarAmt` must be a positive integer.")

    if expirationDate is None:
        _expirationDate = "NULL"
    else:
        _expirationDate = expirationDate.isoformat()

    con = sqlite3.connect(DISCOUNTS_DATABASE)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO discounts VALUES (?, ?, ?, ?, ?)",
        (discountCode, percentage, dollarAmt, freeShipping, _expirationDate),
    )
    con.commit()
    con.close()


# TODO: Implement me!
def updateDiscountInDatabase(
    discountCode: str,
    percentage: int | None = None,
    dollarAmt: int | None = None,
    freeShipping: bool | None = None,
    expirationDate: datetime.datetime | None = None,
):
    """
    The way I think this should work is the following:
    First, get the current information about the row via primary key `discountCode`.
    Unpack that into local variables. Somehow use the _check_add_discount_args() function
    defined above to check whether the caller is updating the row in a valid way. If everything
    is good, call the SQL UPDATE execute statement.
    """
    raise NotImplementedError


class BaseOrder:
    """Base class for derived Order classes."""

    MAX_QUANTITY = 25
    """The maximum number of any individual product allowed in an order."""

    def __init__(self) -> None:
        """Initialise a `BaseOrder`.
        It should be noted that it is usually advised to
        instantiate an `Order` object instead of a `BaseOrder`.
        """
        self.productList: dict[str, int] = dict()
        """productList represented as {UUID: Quantity}"""
        self.orderID: UUID = uuid4()

    def __str__(self) -> str:
        output = f"Order {self.orderID.hex}\n"

        # print entry for each product in order
        for idx, (productUUID, quantity) in enumerate(self.productList.items()):
            try:
                p = products.getProductByUUID(productUUID)
                output += (
                    f"{idx + 1}. {quantity} of {p.name} "
                    f"@ {formatCentsToDollars(p.price)} each\n"
                )
            except products.ProductNotFoundError:
                print(
                    """Something is very wrong with the order... 
                this needs fixing. A product should not have been added to the 
                order if it doesn't exist in the database..."""
                )

        output += f"TOTAL: {formatCentsToDollars(self.totalPrice)}"
        return output

    @property
    def totalPrice(self) -> int:
        """Total price of the order in USD cents."""
        prices = []
        for productUUID, quantity in self.productList.items():
            try:
                p = products.getProductByUUID(productUUID)
                prices.append(p.price * quantity)
            except products.ProductNotFoundError:
                print(
                    """Something is very wrong with the order... 
                this needs fixing. A product should not have been added to the 
                order if it doesn't exist in the database..."""
                )
        return sum(prices)

    def addProduct(self, productUUID: str) -> None:
        """Increment the product with the passed UUID's quantity by one in the
        order, adding the product to the order if it is not already present.

        If `productUUID` is not a valid product (i.e., not added to the
        products database), then a `products.ProductNotFoundError is raised`.
        """
        if not products.productExists(productUUID):
            raise products.ProductNotFoundError

        if (quantity := self.productList.get(productUUID)) is None:
            self.productList[productUUID] = 1
        elif quantity <= self.MAX_QUANTITY:
            self.productList[productUUID] += 1

    def removeProduct(self, productUUID: str) -> None:
        """Decrement the product with the passed UUID's quantity by one from
        the order, removing it entirely if the quantity is only one.

        If the product is not found in the order, this method silently does
        nothing; it is the developer's responsibilty not to pass in a product
        that does not exist in the order (it doesn't make sense to
        intentionally have functionality for removing a product that was never
        added to the order - that would only occur when this method is called
        incorrectly).

        If `productUUID` is not a valid product (i.e., not added to the
        products database), then a `products.ProductNotFoundError is raised`.
        """
        if not products.productExists(productUUID):
            raise products.ProductNotFoundError

        if (val := self.productList.get(productUUID)) == 1:
            self.productList.pop(productUUID)  # key is guaranteed to exist here
        elif val is None:
            pass  # user of this function should never let program reach here
        else:
            self.productList[productUUID] -= 1

    def setQuantity(self, productUUID: str, quantity: int) -> None:
        """Instead of adding or removing a product, this function allows
        setting the quantity of a product directly.

        If a product is not in the order, it will be added to the order.
        If a product's quantity is set to zero, it will be removed from the
        order.

        If `productUUID` is not a valid product (i.e., not added to the
        products database), then a `products.ProductNotFoundError is raised`.
        """
        if not products.productExists(productUUID):
            raise products.ProductNotFoundError

        if quantity == 0:
            self.productList.pop(productUUID)
        elif productUUID not in self.productList.keys():
            self.productList[productUUID] = quantity
        elif quantity <= self.MAX_QUANTITY:
            if self.productList.get(productUUID):
                self.productList[productUUID] = quantity


class Order(BaseOrder):
    """Instances of `Order` contain a user-generated order.
    The `products` argument can be supplied, initialising the Order with a
    An `Order` contains a list of products.
    """

    def __init__(self, orderDict: dict[str, int] | None = None) -> None:
        """Initialise an order. Passing a dictionary of products is optional,
        as products can be added to the order later as needed.

        If passed, `orderDict` is of the form `{ProductUUID: Quantity}`, where
        `ProductUUID` is the product's hexadecimal UUID `str` and `Quantity` is
        an `int`.

        If any product in `orderDict` has a quantity of zero, it is silently not
        added to the order.

        If any product not in the products database is passed via `orderDict`,
        it is silently not added to the order. All passed products should be
        validated (i.e., via `products.productExists()`).
        """
        super().__init__()
        if orderDict:
            self.productList = {
                productUUID: quantity
                for productUUID, quantity in orderDict.items()
                if quantity and products.productExists(productUUID)
            }


class RandomOrder(BaseOrder):
    """An instance of `RandomOrder` contain a randomly generated order.
    This class is essentially only for system testing.
    """

    def __init__(self, numRandomProducts: int) -> None:
        """Initialise an order, with `numRandomProducts` randomly generated products."""
        super().__init__()

        con = sqlite3.connect(products.PRODUCTS_DATABASE)
        cur = con.cursor()
        allProducts: list[tuple] = [
            productUUID for productUUID in cur.execute("SELECT uuid FROM products")
        ]
        con.close()

        random.seed()
        self.productList = {
            random.choice(allProducts)[0]: random.randint(1, 5)
            for _ in range(numRandomProducts)
        }
