import 'react-native-gesture-handler';
import * as React from 'react';
import MapView from 'react-native-maps';
import { UrlTile } from 'react-native-maps';



import {
  View,
  Text,
} from 'react-native';


  class MapLocation extends React.Component { 

    constructor(props) {
      super(props)
      this.state = {
        region: {
          latitude: 37.78825,
          longitude: -122.4324,
          latitudeDelta: 0.0922,
          longitudeDelta: 0.0421,
        },
      }
  }
    
    onRegionChange(region) {
      this.setState({ region });
    }
    
    render() {
      return (
        <MapView
        provider= { undefined}
    />
          //   region={this.state.region}
          //   onRegionChange={this.onRegionChange}
          // >
          //   <UrlTile
          //     /**
          //      * The url template of the tile server. The patterns {x} {y} {z} will be replaced at runtime
          //      * For example, http://c.tile.openstreetmap.org/{z}/{x}/{y}.png
          //      */
          //     urlTemplate={this.state.urlTemplate}
          //     /**
          //      * The maximum zoom level for this tile overlay. Corresponds to the maximumZ setting in
          //      * MKTileOverlay. iOS only.
          //      */
          //     maximumZ={19}
          //     /**
          //      * flipY allows tiles with inverted y coordinates (origin at bottom left of map)
          //      * to be used. Its default value is false.
          //      */
          //     flipY={false}
          //   />
          // </MapView>
      );
    }

  }

  export default MapLocation;

// import * as React from 'react';


// import {
//   View,
//   Text,
//   Button,
// } from 'react-native';
// // import { NavigationContainer, TabActions } from '@react-navigation/native';


// export default function App({ navigation }) {
//   return (
//       <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
//         <Text>Profile photo</Text>
//         {/* <Button title="open drawer"  onPress={() => navigation.openDrawer()}/> */}
//       </View>
//   );
// }