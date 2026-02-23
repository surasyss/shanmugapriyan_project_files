import React from 'react';
import {
  Image, ScrollView, Text, TouchableOpacity, View
} from 'react-native';
import styles from './styles';

export default function InvoicePreview(props) {
  const { image, discard, upload } = props;

  return (
    <ScrollView
      contentContainerStyle={styles.containerStyle}
      style={styles.container}
    >

      <View style={styles.imageContainer}>
        <Image
          source={{ uri: image }}
          style={styles.image}
          resizeMode="contain"
        />

      </View>

      <View style={styles.bottomContainer}>
        <TouchableOpacity onPress={() => discard()}>
          <Text style={styles.buttonTextDanger}>Discard</Text>
        </TouchableOpacity>

        {/* <TouchableOpacity> */}
        {/*  <Text style={styles.buttonText}>Options</Text> */}
        {/* </TouchableOpacity> */}

        <TouchableOpacity onPress={() => upload()}>
          <Text style={styles.buttonText}>Upload</Text>
        </TouchableOpacity>
      </View>

    </ScrollView>
  );
}
