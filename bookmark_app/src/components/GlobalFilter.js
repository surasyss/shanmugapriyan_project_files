import React from 'react'

export const GlobalFilter = ({ globalFilter, setGlobalFilter}) => {

    return (
        <span>
            Filter : {' '}
            <input value={globalFilter || ''} onChange={(e) => setGlobalFilter(e.target.value)}></input>
        </span>
    )
}
