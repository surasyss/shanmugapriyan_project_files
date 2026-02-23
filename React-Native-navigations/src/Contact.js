import * as React from 'react';
import Icon from 'react-native-vector-icons/FontAwesome';
import Contacts from 'react-native-contacts';

import { StyleSheet,
    FlatList,
    View,
    Text,
    Platform,
    Image,
    TouchableOpacity,
    PermissionsAndroid} from 'react-native';

const styles = StyleSheet.create({
    itemContainer: {
        margin: 1
    }
})

class ContactList extends React.Component { 
    constructor(props) {
        super(props)
        this.state = {
            contacts: null
        }
    }
    
    componentDidMount() {
        if (Platform.OS === 'android') {
          PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.READ_CONTACTS, {
              title: "Contacts",
              message: "This app would like to view your contacts."
              }).then(() => {
              this.getList();
              });
        } else if(Platform.OS === 'ios') {
            this.getList();
        }
    }

    getList = () => {
        Contacts.getAll((err, contacts) => {
          if (err === "denied") {
              // error
          } else {
              this.setState({ contacts });
              console.log(contacts[0]);
          }
        });
    }
  
    renderItem = ({item}) => (
        <View style={styles.itemContainer}>
           <TouchableOpacity>
            {/* <Text style={styles.contactName}>
                Name: {`${item.givenName} `} {item.familyName}
            </Text> */}
            <Image source = {require('./white.jpg')}style={{  width: 50, height: 55, borderWidth: 10, borderRadius: 30,left: 20,}} />
            {item.phoneNumbers.map(phone => (
                <Text style={{fontSize:26, left: 99, top: -47,}}>{phone.number}</Text>
            ))}
            </TouchableOpacity> 
        </View>
    )

    render() {
        return (
            <View style={styles.container}>
                <FlatList
                    data={this.state.contacts}
                    renderItem={this.renderItem}
                    //Setting the number of column
                    numColumns={1}
                    keyExtractor={(item, index) => index}
                />
            </View>
        )
    }
}

export default ContactList;