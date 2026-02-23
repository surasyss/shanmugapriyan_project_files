import React, { Component , useEffect} from 'react';
import { CommonActions, useNavigation } from '@react-navigation/native' // <-- import useNavigation hook
import { Platform, StyleSheet, Image, Text, View, Button, WebView } from 'react-native';


export default class App extends React.Component {

    constructor()  {  
        super();  
        this.state = {  
        isConnection: false
        }  

    } 



render() {
      //Hide Splash screen on app load.

    return (
    <View style={styles.container}>
        <Button title="One - drive - login" onPress={() => this.props.navigation.navigate('MicrosoftLoginPage')}/>
    </View>
    )
}

}

// --------------------------------------------------- css part --------------------------------------------------


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