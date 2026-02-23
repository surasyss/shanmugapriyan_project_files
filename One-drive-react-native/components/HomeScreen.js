import 'react-native-gesture-handler';
import React, { Component } from 'react';
import { CommonActions, useNavigation } from '@react-navigation/native' // <-- import useNavigation hook

import { Platform, StyleSheet, Image, Text, View, Button, WebView } from 'react-native';


async function asyncCall() {
  console.log(" -----------  asyncCall ----------");
}




export default class App extends React.Component {

  constructor()  {  
    super();  
   
    console.log("========  Homescreen  =======");
    
    this.state = {  
      isPasswordVisible: true,
      text_access : true,
      access_token: ''
    }  
  } 

  render() {
    return (
       <View style={styles.container}>
           <Button title="One - drive - login" onPress={() => this.props.navigation.navigate('Artical')}/>
        <View><Text></Text></View>

      </View>
    )
}

}


const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F5FCFF',
  },
  welcome: {
    fontSize: 20,
    textAlign: 'center',
    margin: 10,
  },
  instructions: {
    textAlign: 'center',
    color: '#333333',
    marginBottom: 5,
  },
});
