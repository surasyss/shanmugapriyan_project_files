import 'react-native-gesture-handler';
import React from 'react';
import { Text, View } from 'react-native';

import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';

import HomeScreen from './webscreens/HomeScreen';
import MicrosoftLoginPage from './webscreens/MicrosoftLoginPage';
import OneDriveItemsList from './webscreens/OneDriveItemsList';
import FolderInsideList from './webscreens/FolderInsideList';
import ShowFiles from './webscreens/ShowFiles';
import VideoFiles from './webscreens/VideoFiles';
import SearchSingleFile from './webscreens/SearchSingleFile';
import Loader from './webscreens/Loder';
// import LoadingScreen from './webscreens/LoadingScreen';


const Stack = createStackNavigator();


const App: () => Node = () => {


  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="HomeScreen" >
        <Stack.Screen  name="HomeScreen" component={HomeScreen} />
        <Stack.Screen  name="MicrosoftLoginPage" component={MicrosoftLoginPage} />
        <Stack.Screen  name="OneDriveItemsList" component={OneDriveItemsList} />
        <Stack.Screen  name="FolderInsideList" component={FolderInsideList} />
        <Stack.Screen  name="ShowFiles" component={ShowFiles} />
        <Stack.Screen  name="VideoFiles" component={VideoFiles} />
        <Stack.Screen  name="SearchSingleFile" component={SearchSingleFile} />
        <Stack.Screen  name="Loader" component={Loader} />
      </Stack.Navigator>
    </NavigationContainer>
  );


};

export default App;
