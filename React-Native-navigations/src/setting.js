import 'react-native-gesture-handler';
import * as React from 'react';
import Icon from 'react-native-vector-icons/FontAwesome';


import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Button,
  Switch,
  Image
} from 'react-native';

const styles = StyleSheet.create({
  setting: {
    fontWeight: 'bold',
    fontSize: 28,
    top: -35, 
    left: -102
    // justifyContent: 'space-around',
  },
  image: {
    width: 250,
    height: 250,
    borderRadius: 125,
    borderWidth: 5,
    borderColor: '#4cfcf3',
    marginBottom: 20,
  },
  AccountText: {
    fontSize: 23,
    fontWeight: 'bold',
    top: 35,
    left: -40,
  },
  NotificationText: {
    fontSize: 23,
    fontWeight: 'bold',
    top: -40,
    left: -55,
  },
});

class SettingsPage extends React.Component { 

  goBack() {
    const { navigation } = this.props;
    navigation.goBack();
    navigation.state.params.onSelect({ selected: true });
  }

  constructor(props){
    super(props);
    this.state = {
    FlatListItems: [{name:'Edit Profile'},{name:'Change password'},{name:'Blacked users'},{name:'Peterson'},{name:'Schwarzenneger'},{name:'Dostoyevsky'}],
    };
    }

    state = {switchValue:false}
    toggleSwitch = (value) => {
        //onValueChange of the switch this function will be called
        this.setState({switchValue: value})
        //state changes according to switch
        //which will result in re-render the text
     }

  render() {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <TouchableOpacity onPress={() => this.props.navigation.goBack(null)}>
          <View style={{ height: -5, width: 53, left: -150}} >
            <Image source = {require('./previous.png') }
              style={{ width: 19, height: 28, top: 0}}>
            </Image>
          </View>
        </TouchableOpacity>
        <Text style={styles.setting} onPress={() => this.props.navigation.goBack(null)}>Settings</Text>
        <View style={{ top: -60 }}>
           <Image source = {require('./profile.png')}style={{ top: 65, width: 24, height: 28, left: -85}} />
           <Text style={styles.AccountText}>Account</Text>
           <Image source = {require('./Left.png')}style={{ top: 58, width: 23, height: 28, left: 220, opacity: 0.2 }} />
           <Text style={{ top: 25, left: -85, fontSize: 20, color: 'rgba(0,0,0,0.3)'}}>Edit profile</Text>
           <Image source = {require('./Left.png')}style={{ top: 48, width: 23, height: 28, left: 220,  opacity: 0.2}} />
           <Text style={{ top: 10, left: -85, fontSize: 20, fontSize: 20, color: 'rgba(0,0,0,0.3)'}}>change password</Text>
           <Image source = {require('./Left.png')}style={{ top: 38, width: 23, height: 28, left: 220,  opacity: 0.2}} />
           <Text style={{ top: 0, left: -85, fontSize: 20, fontSize: 20, color: 'rgba(0,0,0,0.3)'}}>Blocked user</Text>
           <Image source = {require('./Left.png')}style={{ top: 28, width: 23, height: 28, left: 220,  opacity: 0.2}} />
           <Text style={{ top: -10, left: -85, fontSize: 20, fontSize: 20, color: 'rgba(0,0,0,0.3)'}}>Logout</Text>
        </View>
        <View style={{top: -30 }}>
          <Image source = {require('./Notification.png')}style={{ top: -10, width: 28, height: 28, left: -100,}} />
          <Text style={styles.NotificationText}>Notification</Text>
          <Text style={{ fontSize: 20,left: -100,top: -20, color: 'rgba(0,0,0,0.3)'}}>Near by people</Text>
          <Switch style={{left: 100, top: -40}} onValueChange = {this.toggleSwitch}
          value = {this.state.switchValue}/>
          <Text style={{ fontSize: 20, left: -100,top: -30, color: 'rgba(0,0,0,0.3)'}}>Popup card</Text>
          <Switch style={{left: 100, top: -55}} onValueChange = {this.toggleSwitch}
          value = {this.state.switchValue}/>
        </View>
      </View>
    );

  }
}


export default SettingsPage;