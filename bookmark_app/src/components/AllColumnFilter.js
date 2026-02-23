import React, { useMemo} from 'react';
import { useTable, useSortBy, useGlobalFilter, useFilters } from "react-table";
import MOCK_DATA from './MOCK_DATA.json';
import { COLNUMNS } from './columns';
import { FaCaretSquareUp, FaCaretSquareDown } from "react-icons/fa";
import './table.css';
import { GlobalFilter } from './GlobalFilter';

export const AllColumnFilter = () => {

    const columns = useMemo(() => COLNUMNS, []);
    const data = useMemo(() => MOCK_DATA, []);

    const {
    getTableProps,
    getTableBodyProps,
    headerGroups,
    rows,
    prepareRow,
    state,
    setGlobalFilter
    } = useTable({ columns, data }, useFilters, useGlobalFilter, useSortBy);

    const { globalFilter } = state;

    return (
    <>
    <GlobalFilter globalFilter={globalFilter} setGlobalFilter={setGlobalFilter} />
    <table {...getTableProps()}>
        <thead>
        {headerGroups.map(headerGroup => (
            <tr {...headerGroup.getHeaderGroupProps()}>
            {headerGroup.headers.map(column => (
                <th>
                    {column.render("Header")}
                    <div>{column.canFilter ? column.render("Filter"): null}</div>
                </th>
            ))}
            </tr>
        ))}
        </thead>
        <tbody {...getTableBodyProps()}>
        {rows.map(row => {
            prepareRow(row);

            return (
            <tr {...row.getRowProps()}>
                {row.cells.map(cell => {
                return (
                    <td {...cell.getCellProps()}>{cell.render("Cell")}</td>
                );
                })}
            </tr>
            );
        })}
        </tbody>
    </table>
    </>
    )
}
