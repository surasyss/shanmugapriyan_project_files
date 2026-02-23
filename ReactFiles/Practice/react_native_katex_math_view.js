/* eslint-disable prettier/prettier */
import React from 'react';
import { StyleSheet, View } from 'react-native';
import Katex from 'react-native-katex';

const App = () => {
  // The LaTeX equation string with all backslashes escaped (doubled)
  const equation = `
    \\Delta \\phi = \\mathbf{E} \\cdot \\Delta \\mathbf{S}
  = \\frac{q}{4\\pi\\varepsilon_0 r^2} \\hat{\\mathbf{r}} \\cdot \\Delta \\mathbf{S}
  `.trim();

  return (
    <View style={styles.container}>
      <View style={styles.equationContainer}>
        {/* Pass the escaped string to the 'expression' prop */}
        {/* <Katex
          expression={equation}
          style={styles.katex}
          displayMode={true} // Set displayMode to true for block-level display
          throwOnError={false} // Prevents app crash if there is a LaTeX error
          errorColor="#f00"
        /> */}
        <Katex
          expression={equation}
          displayMode={true}
          errorColor="#f00"
          // Only use internal props here; avoid layout styles
          inlineStyle={`
            html, body { 
              background-color: transparent; 
              font-size: 35px; 
            }
          `}
        />
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  equationContainer: {
    padding: 10,
    borderWidth: 1,
    height: 200,
    width: '100%',
    backgroundColor: '#f9f9f9',
    opacity: 0.99,
  },
  katex: {
    // Custom styles for the rendered equation (e.g., font size)
    fontSize: 30,
  },
});

export default App;

