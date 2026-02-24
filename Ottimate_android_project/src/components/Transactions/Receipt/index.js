import React from 'react';
import {
  Text, TouchableOpacity, View, Image, ActivityIndicator
} from 'react-native';
import Pdf from 'react-native-pdf';
import Icon from 'react-native-vector-icons/dist/FontAwesome';
import styles from './styles';
import { formatReceiptTakenAt } from '../../../utils/DateFormatter';
import Colors from '../../../styles/Colors';
import PercentageLoader from '../../qubiqle/PercentageLoader';

export default class Receipt extends React.PureComponent {
  constructor() {
    super();
    this.state = {
      loading: true
    };
  }

  render() {
    const {
      receipt, onPress
    } = this.props;

    if (receipt) {
      const {
        created_date, file_url, progress, created_user_name, isCreated
      } = receipt;
      const extension = file_url.split('.').reverse()[0];
      return (
        <TouchableOpacity
          style={styles.mainView}
          onPress={() => {
            if (onPress) {
              onPress(receipt);
            }
          }}
        >
          <View style={styles.container}>
            <View>
              {
                extension.toLowerCase() === 'pdf'
                  ? (
                    <Pdf
                      source={{ uri: file_url }}
                      style={styles.pdf}
                      onLoadComplete={() => this.setState({ loading: false })}
                    />
                  )
                  : (
                    <Image
                      source={{ uri: file_url }}
                      style={styles.image}
                      resizeMode="contain"
                      onLoadStart={() => this.setState({ loading: true })}
                      onLoadEnd={() => this.setState({ loading: false })}
                    />
                  )
              }
              <ActivityIndicator animating={this.state.loading} style={styles.loader} />
            </View>
            <View style={styles.rightContainer}>
              <Text style={styles.user}>
                {created_user_name}
              </Text>
              <Text style={styles.date}>
                {formatReceiptTakenAt(created_date)}
              </Text>
            </View>
          </View>
          <ProgressView progress={progress} isCreated={isCreated} />

        </TouchableOpacity>
      );
    }
    return <View />;
  }
}

function ProgressView(props) {
  const { progress, isCreated } = props;

  if (isCreated) {
    return (
      <Icon
        name="check-circle"
        style={styles.done}
      />
    );
  }

  if (progress !== undefined) {
    return (
      <PercentageLoader
        radius={20}
        percent={progress}
        color={Colors.primary}
        bgcolor={Colors.secondaryText}
      />
    );
  }

  return null;
}
