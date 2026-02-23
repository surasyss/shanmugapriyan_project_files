import 'react-native-gesture-handler';
import * as React from 'react';
import { NavigationContainer, TabActions } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { createDrawerNavigator, DrawerContentScrollView,
  DrawerItemList,
  DrawerItem } from '@react-navigation/drawer';
// import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createMaterialTopTabNavigator } from '@react-navigation/material-top-tabs';
import Setting from './src/setting';
import LogsPage from './src/Logs';
import ContactPage from './src/Contact';
import LocationPage from './src/Logation';
import ActionBarImage from './src/imagefile';


import {
  SafeAreaView,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  View,
  Text,
  Image,
  Button
} from 'react-native';

import {
  Header,
  LearnMoreLinks,
  Colors,
  DebugInstructions,
  ReloadInstructions,
} from 'react-native/Libraries/NewAppScreen';
import { ScreenContainer } from 'react-native-screens';

// function HomeScreen({ navigation }) {
//   return (
//     <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
//       <Text>Home Screen</Text>
//       <Button
//         title="Go to Details"
//         onPress={() => navigation.navigate('Details')}
//       />
//     </View>
//   );
// }


function CustomDrawerContent(props) {
  return (
    <DrawerContentScrollView {...props}>
      <DrawerItemList {...props} />
      <DrawerItem
        label="Close drawer"
        onPress={() => props.navigation.closeDrawer()}
      />
    </DrawerContentScrollView>
  );
}

const Stack = createStackNavigator();
const Tabs = createMaterialTopTabNavigator();
const Drawer = createDrawerNavigator();

// const HomeStack = createStackNavigator();
// const DetailStack = createStackNavigator();


// const HomeStackScreen = () => (
//   <HomeStack.Navigator>
//     <HomeStack.Screen name= "Home" component={HomeReal} /> 
//   </HomeStack.Navigator>

// );

// const DetailStackScreen = () => (
//   <DetailStack.Navigator>
//     <DetailStack.Screen name= "Details" component={DetailsReal} /> 
//   </DetailStack.Navigator>

// );

const InTab = () => (
  <Tabs.Navigator 
    tabBarOptions={{
      activeTintColor: 'white',
      inactiveTintColor: "white",
      indicatorStyle :{
        backgroundColor:'white'
      },
      labelStyle: { fontSize: 14 },
      style: { backgroundColor: '#0A63C3', height: 50 },
    }} 
    >
    <Tabs.Screen name="LOGS" component={LogsPage} />
    <Tabs.Screen name="CONTACTS" component={ContactPage} />
    <Tabs.Screen name="LOCATION" component={LocationPage} />
    {/* <Tabs.Screen name="LOCATION" component={LocationPage} /> */}
  </Tabs.Navigator>  
);


const SecTab = ({ navigation }) => (
  <Stack.Navigator>
     <Stack.Screen name="Turst Call" component={InTab} 
        options={{
          title: 'Trust Call',
          headerRight : props => <TouchableOpacity onPress={() => navigation.openDrawer()}><Image source = {require('./src/option.png')}style={{ width: 25, height: 18, left: -10}} /></TouchableOpacity>,
          // headerTitle: props => <ActionBarIcon {...props} />,
          headerStyle: {
            backgroundColor: '#0A63C3',
            height: 75
          },
          headerTintColor: '#fff',
          headerTitleStyle: {
            // fontWeight: 'bold',
            fontSize: 27,
            left: 10
          },
        }}
     />
  </Stack.Navigator>
);

function App() {
  return (
    <NavigationContainer>
      <Drawer.Navigator drawerContent={props => <CustomDrawerContent {...props} />} >
        <Drawer.Screen name="SecTab" component={SecTab} />
        <Drawer.Screen name="Settings" component={Setting} />
      </Drawer.Navigator>
    </NavigationContainer>
  );
}

export default App;