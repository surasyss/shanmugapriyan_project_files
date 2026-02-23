import React from 'react';
import {
  Image, Text, TouchableOpacity, View
} from 'react-native';
import styles from './styles';
import Images from '../../../styles/Images';

export default function DeleteInvoice(props) {
  const { invoice, close, deleteImage } = props;

  return (
    <View style={styles.container}>
      <View style={styles.topBar}>
        <TouchableOpacity onPress={() => deleteImage()}>
          <Text style={styles.deleteText}>Delete</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.closeButton} onPress={() => close()}>
          <Image
            source={Images.camera_close}
            style={styles.closeIcon}
            resizeMode="contain"
          />
        </TouchableOpacity>
      </View>

      <Image
        source={{ uri: invoice.image }}
        style={styles.image}
      />
    </View>
  );
}
