import React from 'react';
import {
  Text, TouchableOpacity, View, ActivityIndicator
} from 'react-native';
import Pdf from 'react-native-pdf';
import styles from './styles';
import Colors from '../../../styles/Colors';

export default function PaymentCheck(props) {
  const {
    image, index, count, onPress
  } = props;
  const numberViews = [styles.oddView, styles.evenView];

  return (
    <TouchableOpacity
      style={[styles.mainView, numberViews[index % 2]]}
      onPress={() => onPress(image, index, count)}
    >
      <Pdf
        source={{ uri: image }}
        style={styles.image}
        pointerEvents="none"
        activityIndicator={<ActivityIndicator size="large" />}
        activityIndicatorProps={{ color: Colors.primary, progressTintColor: Colors.primary }}
      />

      <View style={styles.waterMarkView}>
        <Text style={styles.waterMark}>
          {index + 1}
          /
          {count}
        </Text>
      </View>

    </TouchableOpacity>
  );
}
