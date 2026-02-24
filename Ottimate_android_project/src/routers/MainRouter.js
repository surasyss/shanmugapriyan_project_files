import React from 'react';
import { StatusBar, View } from 'react-native';
import SwitchNavigator from './SwitchNavigator';
import Colors from '../styles/Colors';

export default function MainRouter() {
  return (
    <View style={{ flex: 1 }}>
      <StatusBar hidden={false} backgroundColor={Colors.primary} />
      <SwitchNavigator />
    </View>
  );
}
