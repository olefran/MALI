BLOCK_SIZE = 1_000
TYPES_AMOUNT = 6

DATA_LOWER_LIMIT = 1_000
DATA_UPPER_LIMIT = DATA_LOWER_LIMIT + BLOCK_SIZE * TYPES_AMOUNT - 1

INSTANCE_LOWER_LIMIT = 7_000
ATTRIBUTE_LOWER_LIMIT = INSTANCE_LOWER_LIMIT
ATTRIBUTE_UPPER_LIMIT = ATTRIBUTE_LOWER_LIMIT + BLOCK_SIZE * TYPES_AMOUNT - 1
PROCEDURE_LOWER_LIMIT = ATTRIBUTE_UPPER_LIMIT
VAR_LOWER_LIMIT = 13_000
VAR_UPPER_LIMIT = VAR_LOWER_LIMIT + BLOCK_SIZE * TYPES_AMOUNT - 1
TEMP_LOWER_LIMIT = VAR_UPPER_LIMIT+1
TEMP_UPPER_LIMIT = TEMP_LOWER_LIMIT + BLOCK_SIZE * TYPES_AMOUNT - 1
PROCEDURE_UPPER_LIMIT = TEMP_UPPER_LIMIT
INSTANCE_UPPER_LIMIT = PROCEDURE_UPPER_LIMIT

CTE_LOWER_LIMIT = INSTANCE_UPPER_LIMIT
CTE_UPPER_LIMIT = CTE_LOWER_LIMIT + BLOCK_SIZE * TYPES_AMOUNT - 1
