import 'react-native-gesture-handler';
import React, { Component , useEffect} from 'react';
import { CommonActions, useNavigation } from '@react-navigation/native' // <-- import useNavigation hook
import { Platform, StyleSheet, Image, Text, View, Button, WebView } from 'react-native';
import NetInfo from "@react-native-community/netinfo";


export default class App extends React.Component {

  constructor()  {  
    super();  
    this.state = {  
      isConnection: false
    }  

    this.checkNetworkConnection();
  } 

  checkNetworkConnection(){
    NetInfo.addEventListener(networkState => {
      console.log("Connection type - ", networkState.type);
      console.log("Is connected? - ", networkState.isConnected);
      this.setState({ isConnection : networkState.isConnected})
    });
  }


  render() {
      //Hide Splash screen on app load.

    return (
       <View style={styles.container}>
         <Button title="One - drive - login" onPress={() => this.props.navigation.navigate('MicrosoftLogin')}/>
         {/* {this.state.isConnection ?
         <Button title="One - drive - login" onPress={() => this.props.navigation.navigate('MicrosoftLogin')}/>
         : <Text style={styles.errorText} >Oops! Looks like your device is not connected to internet. Please turn on your net connection. </Text> } */}
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
  errorText:{
    fontSize : 28,
    fontFamily : 'Serif' 
  },
});
