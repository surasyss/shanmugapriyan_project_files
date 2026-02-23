import { format } from "date-fns";
import { ColumnFilter } from "./ColumnFilter";


export const COLNUMNS = [
    {
        Header: 'Id',
        accessor: 'id',
        Filter: ColumnFilter,
        disableFilters: true   // reomove filter.
    },
    {
        Header: 'First Name',
        accessor: 'first_name',
        Filter: ColumnFilter
    },
    {
        Header: 'Last Name',
        accessor: 'last_name',
        Filter: ColumnFilter
    },
    {
        Header: 'Email',
        accessor: 'email',
        Filter: ColumnFilter
    },
    {
        Header: 'Date of Birth',
        accessor: 'date_of_birth',
        Cell: ({ value }) => { return format(new Date(value), 'dd/MM/yyyy')},
        Filter: ColumnFilter
    },
    {
        Header: 'Country',
        accessor: 'county',
        Filter: ColumnFilter
    },
    {
        Header: 'Phone',
        accessor: 'phone',
        Filter: ColumnFilter
    },
]
