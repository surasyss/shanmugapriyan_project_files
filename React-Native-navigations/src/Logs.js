import 'react-native-gesture-handler';
import React, { Component } from 'react';
//Import React
import {
  Platform,
  StyleSheet,
  Text,
  View,
  PermissionsAndroid,
  FlatList,
  TouchableOpacity,
  Image
  
} from 'react-native';
//Import all the basic component from React Native Library
import CallLogs from 'react-native-call-log';
//Import library to access call log

export default class App extends Component {
  constructor(props) {
    super(props);
    //Make default blank array to store details
    this.state = {
      FlatListItems: [],
    };
  }
  componentDidMount = async () => {
    if (Platform.OS != 'ios') {
      try {
        //Ask for runtime permission
        const granted = await PermissionsAndroid.request(
          PermissionsAndroid.PERMISSIONS.READ_CALL_LOG,
          {
            title: 'Call Log Example',
            message: 'Access your call logs',
            buttonNeutral: 'Ask Me Later',
            buttonNegative: 'Cancel',
            buttonPositive: 'OK',
          }
        );
        if (granted === PermissionsAndroid.RESULTS.GRANTED) {
          CallLogs.loadAll().then(c => this.setState({ FlatListItems: c }));
          CallLogs.load(3).then(c => console.log(c));
        } else {
          alert('Call Log permission denied');
        }
      } catch (e) {
        alert(e);
      }
    } else {
      alert(
        'Sorry! You can’t get call logs in iOS devices because of the security concern'
      );
    }
  };

  FlatListItemSeparator = () => {
    return (
      //Item Separator
      <View
        style={{ height: 0.5, width: '100%' }}
      />
    );
  };

//   renderItem = ({item}) => (
//     <View style={styles.itemContainer}>
//        <TouchableOpacity>
//         {/* <Text style={styles.contactName}>
//             Name: {`${item.givenName} `} {item.familyName}
//         </Text> */}
//         <Image source = {require('./white.jpg')}style={{ width: 60, height: 65, borderWidth: 1, borderRadius: 30,left: 20,}} />
//         <Text style={styles.item}>
//                 Name : {item.name ? item.name : 'NA'}
//                 {'\n'}
//                 {/* DateTime : {item.dateTime}
//                 {'\n'}
//                 Duration : {item.duration}
//                 {'\n'} */}
//                 PhoneNumber : {item.phoneNumber}
//                 {'\n'}
//                 {/* RawType : {item.rawType}
//                 {'\n'}
//                 Timestamp : {item.timestamp}
//                 {'\n'}
//                 Type : {item.type} */}
//               </Text>
//         </TouchableOpacity> 
//     </View>
// )

  render() {
    return (
      <View >
        <FlatList
          data={this.state.FlatListItems}
          ItemSeparatorComponent={this.FlatListItemSeparator}
          renderItem={({ item }) => (
            // Single Comes here which will be repeatative for the FlatListItems
            <View style={{ margin: -20 }}>
              <TouchableOpacity>
                {/* <Text style={styles.contactName}>
                    Name: {`${item.givenName} `} {item.familyName}
                </Text> */}
                <Image source = {require('./white.jpg')}style={{ width: 50, height: 55, borderWidth: 10, borderRadius: 30,left: 35, top: 25}} />
                <Text style={styles.item}>
                  {item.name ? item.name : 'Unknown'}
                  {'\n'}
                  {item.dateTime}
                  {'\n'}
                  {/* Duration : {item.duration}
                  {'\n'}  */}
                  {item.phoneNumber}
                  {'\n'}
                  {/* RawType : {item.rawType}
                  {'\n'}
                  Timestamp : {item.timestamp}
                  {'\n'}
                  Type : {item.type} */}
                </Text>
              </TouchableOpacity> 
            </View>
          )}
          numColumns={1}
          keyExtractor={(item, index) => index}
        />
      </View>
    );
  }
}
const styles = StyleSheet.create({

  item: {
    top: -25,
    left: 115,
    fontSize: 18,
  },
  itemContainer: {
    margin: 1
  }
});
