from spices.django3.fields import PrefixedIdField


def _prepare_fk_table_sql(
    main_table_name,
    related_table_name,
    fk_column_name,
    fk_constraint_name,
    fk_column_not_null,
    fk_column_unique_constraint,
    related_table_other_constraints=None,
):
    _sql = "\n\n"

    # add temp column
    _sql += f"""ALTER TABLE {related_table_name}
        ADD COLUMN "{fk_column_name}_str" text
        {fk_column_unique_constraint};
    """

    # populate {fk_column_name}_str by joining with main table
    _sql += f"""
        UPDATE {related_table_name}
        SET "{fk_column_name}_str" = "{main_table_name}"."id_str"
        FROM {main_table_name}
        WHERE "{main_table_name}"."id" = "{related_table_name}"."{fk_column_name}";
    """

    # Now that we have populated it, make column NOT NULL if it was so
    if fk_column_not_null:
        _sql += f'\n ALTER TABLE {related_table_name} ALTER "{fk_column_name}_str" SET NOT NULL;'

    # drop FK constraint
    _sql += f"\n ALTER TABLE {related_table_name} DROP CONSTRAINT {fk_constraint_name};"

    # drop other constraints that may be dependent on this old FK column
    if related_table_other_constraints and related_table_other_constraints.get("drop"):
        _sql += f'\n {related_table_other_constraints["drop"]} ;'

    # We will rename the old column instead of dropping it for verification purposes
    # _sql += f'\n ALTER TABLE {related_table_name} DROP COLUMN "{fk_column_name}";'
    _sql += f'\n ALTER TABLE {related_table_name} RENAME COLUMN "{fk_column_name}" TO "{fk_column_name}_old";'

    # rename FK_str column to FK column
    _sql += f'\n ALTER TABLE {related_table_name} RENAME COLUMN "{fk_column_name}_str" TO "{fk_column_name}";'

    # Lastly, while we let the old column remain for validation,
    # we don't want it to interfere with normal functioning, so make it nullable
    if fk_column_not_null:
        _sql += f'\n ALTER TABLE {related_table_name} ALTER COLUMN "{fk_column_name}_old" DROP NOT NULL;'

    # add back other constraints that may be dependent on the new FK column
    if related_table_other_constraints and related_table_other_constraints.get("add"):
        _sql += f'\n {related_table_other_constraints["add"]} ;'

    # we do not add back the FK constraint here because the main table PKEY isn't set yet
    _add_fk_constraints_sql = f"""
        ALTER TABLE {related_table_name}
        ADD CONSTRAINT "{fk_constraint_name}"
        FOREIGN KEY ({fk_column_name})
        REFERENCES "{main_table_name}"("id")
        DEFERRABLE INITIALLY DEFERRED ;
    """

    return _sql, _add_fk_constraints_sql


def _prepare_main_table_sql(table_name, prefix, downstream_tables=(), pkey_name=None):
    if not pkey_name:
        pkey_name = f"{table_name}_pkey"

    prefixed_id_field = PrefixedIdField(prefix)
    key_length = prefixed_id_field.key_length
    _sql = ""

    _sql += f"""ALTER TABLE {table_name}
        ADD COLUMN "id_str" text NOT NULL
        DEFAULT ('{prefix}_' || base_model_key_generator({key_length}));
    """

    _add_fk_constraints_sql = ""
    for fk_kwargs in downstream_tables:
        _fk_sql, _fk_add_const_sql = _prepare_fk_table_sql(table_name, **fk_kwargs)
        _sql += _fk_sql
        _add_fk_constraints_sql += _fk_add_const_sql

    _sql += f"\n ALTER TABLE {table_name} DROP CONSTRAINT {pkey_name};"

    # We will rename the old column instead of dropping it for verification purposes
    # _sql += f'\n ALTER TABLE {table_name} DROP COLUMN "id";'
    _sql += f'\n ALTER TABLE {table_name} RENAME COLUMN "id" TO "id_old";'

    _sql += f'\n ALTER TABLE {table_name} RENAME COLUMN "id_str" TO "id";'
    _sql += f'\n ALTER TABLE {table_name} ADD CONSTRAINT {table_name}_pkey PRIMARY KEY ("id");'
    # _sql += f'\n CREATE UNIQUE INDEX "{table_name}_id_key" ON {table_name} ("id"); '

    # lastly, while we let the old id column remain for validation,
    # we don't want it to interfere with normal functioning, so make it nullable
    _sql += f'\n ALTER TABLE {table_name} ALTER COLUMN "id_old" DROP NOT NULL;'

    # add back all unique constraints
    _sql += _add_fk_constraints_sql

    return _sql


def prepare_sql_for_pk_datatype_update(tables):
    """
    # Strictly speaking, order shouldn't matter, but only tested to go one way (leaf first)
    # Go Leaf Table -> upwards
    """
    sql = ""
    for kwargs in tables:
        sql += "\n-------------\n\n" + _prepare_main_table_sql(**kwargs)

    return sql


def migration_print_sql(sql):
    # noinspection PyUnusedLocal
    def forward(apps, schema_editor):  # pylint: disable=unused-argument
        print("\n------------------ Generated SQL -----------------\n")
        print(sql)
        print("\n---------------------- (end) ---------------------\n")

    return forward
