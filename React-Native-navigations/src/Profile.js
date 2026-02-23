import 'react-native-gesture-handler';
import * as React from 'react';


import {
  View,
  Text,
  Button,
} from 'react-native';
import { NavigationContainer, TabActions } from '@react-navigation/native';


export default function App({ navigation }) {
  return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <Text>Profile photo</Text>
        {/* <Button title="open drawer"  onPress={() => navigation.openDrawer()}/> */}
      </View>
  );
}