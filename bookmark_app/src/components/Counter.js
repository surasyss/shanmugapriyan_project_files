import React, { Component } from 'react';
import './counter.css'

export class Counter extends Component {

    constructor()  {  
        super();  
        this.state = {  
            counter : 0
        }
    }

    componentDidMount(){
        console.log("--------- componentDidMount ----------")
    }

    componentDidUpdate(){
        console.log("---------|| componentDidUpdate ||----------")
    }

    componentWillUnmount(){
        console.log("===========|| componentWillUnmount ||===========")
    }

    clickOnMe = () => {
        this.setState({ counter : this.state.counter + 1})
    }

    decrement = () =>{
        this.setState({ counter : this.state.counter - 1})
    }


    render() {
        console.log("--------- render ----------")
        return (
            <div className='mainDiv'>
                <button onClick={() => this.clickOnMe()}>Counter</button>
                <div>Hello  {this.state.counter}</div>
                <button onClick={() => this.decrement()}>DEC</button>
            </div>
        )
    }
    
}

