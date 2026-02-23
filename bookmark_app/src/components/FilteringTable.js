import React, { useMemo} from 'react';
import { useTable, useSortBy, useGlobalFilter } from "react-table";
import MOCK_DATA from './MOCK_DATA.json';
import { COLNUMNS } from './columns';
import { FaCaretSquareUp, FaCaretSquareDown } from "react-icons/fa";
import './table.css';
import { GlobalFilter } from './GlobalFilter';

export const FilteringTable = () => {

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
    } = useTable({ columns, data }, useGlobalFilter, useSortBy);

    const { globalFilter } = state;

    return (
    <>
    <GlobalFilter globalFilter={globalFilter} setGlobalFilter={setGlobalFilter} />
    <table {...getTableProps()}>
        <thead>
        {headerGroups.map(headerGroup => (
            <tr {...headerGroup.getHeaderGroupProps()}>
            {headerGroup.headers.map(column => (
                <th {...column.getHeaderProps(column.getSortByToggleProps())}>
                {column.render("Header")}
                <span>
                {column.isSorted ? (
                    column.isSortedDesc ? (
                    <FaCaretSquareDown />
                    ) : (
                    <FaCaretSquareUp />
                    )
                ) : (
                    ""
                )}
                </span>
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
