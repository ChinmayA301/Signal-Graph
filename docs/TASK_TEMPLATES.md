# TASK_TEMPLATES.md

## Add a new scoring feature

When adding a scoring feature, complete all of the following:

1. define the feature clearly
2. identify required raw inputs
3. implement pure computation function
4. normalize into a subscore if needed
5. add explanation text mapping feature → interpretation
6. expose raw and normalized values in API response
7. add tests
8. update scoring spec docs (`docs/SCORING_SPEC.md`)

## Add a new API endpoint

1. define endpoint contract
2. add request/response schemas
3. add service logic
4. keep route handler thin
5. add typed frontend consumption if needed
6. add tests
7. document endpoint in `README.md` or `docs/`

## Add a new database field

1. update ORM model
2. create Alembic migration
3. update Pydantic schemas
4. update shared types
5. update any affected UI
6. document if semantic meaning changes (`docs/DATA_DICTIONARY.md`)

## Add a new dashboard panel

1. identify exact data contract
2. build UI component
3. add loading and error states
4. add empty-data state
5. support explanation display where relevant
6. ensure type safety end-to-end
