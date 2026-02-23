import React, { Component } from 'react';
import logo from './logo.svg';
import './App.css';
import { BasicTable } from './components/BasicTable';
import { SortingTable } from './components/SortingTable';
import { FilteringTable } from './components/FilteringTable';
import { AllColumnFilter} from './components/AllColumnFilter';
import { PaginationTable } from './components/PaginationTable';
import { RowSelection } from './components/RowSelection';
import { Counter } from './components/Counter';

class App extends Component {
  constructor(){
    super();
    this.state = {
      mount : true
    }
  }

  mounting = () => { this.setState({ mount : true }) };
  unmounting = () => { this.setState({ mount : false }) };

  render(){
    return (
    <>
      <div>
        <button onClick={() => this.mounting()}>mounting</button>
        <button onClick={() => this.unmounting()}>unmounting</button>
      </div>
      <div>
        {this.state.mount ? <Counter /> : null}
      </div>
    </>
    )
  }
}

export default App;
